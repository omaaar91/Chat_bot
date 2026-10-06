import os
import sys
from dotenv import load_dotenv

# دعم طباعة الحروف العربية في موجه الأوامر على ويندوز
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# تحميل متغيرات البيئة
load_dotenv()

from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# مسارات المشروع
instructions_path = "chatbot_instructions.txt"
pdf_path = "Chatbot_Instructions_Complete.pdf"
db_dir = "./chroma_db_v2"

# 1. إعداد نموذج التضمين (Embeddings - يدعم العربية والإنجليزية معاً)
embeddings = FastEmbedEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# 2. بناء أو تحميل قاعدة بيانات المتجهات (ChromaDB - SQLite)
if not os.path.exists(db_dir) or not os.path.exists(os.path.join(db_dir, "chroma.sqlite3")):
    if os.path.exists(instructions_path):
        print(f"[*] جاري قراءة البيانات من: {instructions_path}...")
        loader = TextLoader(instructions_path, encoding="utf-8")
    else:
        print(f"[*] جاري قراءة البيانات من: {pdf_path}...")
        loader = PyPDFLoader(pdf_path)

    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=40,
    )
    chunks = text_splitter.split_documents(documents)
    print(f"[OK] تم تقسيم النص إلى {len(chunks)} مقطع.")

    print(f"[*] جاري إنشاء وتخزين المتجهات في {db_dir}...")
    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=db_dir
    )
    print(f"[SUCCESS] تم حفظ قاعدة البيانات بنجاح في {db_dir}/chroma.sqlite3")
else:
    print(f"[OK] تم تحميل قاعدة البيانات المحفوظة مسبقاً من: {db_dir}")
    vector_db = Chroma(
        persist_directory=db_dir,
        embedding_function=embeddings
    )

# 3. إعداد المسترجع (Retriever) لجلب المقاطع المطابقة لسؤال العميل
retriever = vector_db.as_retriever(search_kwargs={"k": 6})

# 4. إعداد موديل الذكاء الاصطناعي (Groq)
llm = ChatGroq(
    model=os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.2
)

# 5. قالب البرومبت لدمج السياق وتاريخ المحادثة مع السؤال
prompt = ChatPromptTemplate.from_template("""أنت مساعد ذكي ومندوب مبيعات لمتجرنا لبيع الكتب في مدينة السادات.
مهمتك هي الإجابة عن استفسارات العملاء بدقة ولباقة باللغة العربية بناءً على السياق المتاح في المتجر.
- إذا سأل العميل عن تصنيف معين أو كتب محددة، اذكر أسماء الكتب المتوفرة، أسعارها، وضع رابط الشراء المباشر لكل كتاب كما ورد في البيانات.
- إذا سأل عن عنوان المتجر، مواعيد العمل، أو سياسة الاسترجاع، أجب بالمعلومات المحددة في التعليمات.
- ساعد العميل في إتمام طلبه وفق بروتوكول إقفال الأوردر خطوة بخطوة إذا أراد الشراء.

السياق (Context):
{context}

سجل المحادثة السابقة:
{chat_history}

سؤال العميل الحالي:
{question}

الإجابة:""")

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# 6. بناء الـ RAG Chain
rag_chain = (
    {
        "context": (lambda x: x["question"]) | retriever | format_docs,
        "chat_history": lambda x: x.get("chat_history", "لا يوجد سجل سابق."),
        "question": lambda x: x["question"]
    }
    | prompt
    | llm
    | StrOutputParser()
)

def ask_bot(question: str, chat_history: str = "") -> str:
    """إرسال السؤال وسجل المحادثة إلى الـ RAG Chain وتوليد الإجابة"""
    return rag_chain.invoke({"question": question, "chat_history": chat_history})


# ==========================================
# تشغيل تجريبي للسؤال
# ==========================================
if __name__ == "__main__":
    test_question = "اي الاقسام عندكو ؟"
    print(f"\n❓ السؤال: {test_question}")
    print("[*] جاري البحث في قاعدة البيانات وتوليد الإجابة...")
    
    answer = ask_bot(test_question)
    print("\n💬 إجابة البوت:")
    print(answer)
