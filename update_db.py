import os
import sys
import shutil
import pandas as pd
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_chroma import Chroma

excel_path = "Ecommerce_Database.xlsx"
instructions_path = "chatbot_instructions.txt"
db_dir = "./chroma_db_v2"

print("[*] جاري قراءة بيانات المنتجات من ملف الإكسيل:", excel_path)
df = pd.read_excel(excel_path, sheet_name="Products")

# ترجمة التصنيفات
category_translations = {
    "Music": "موسيقى وأغاني",
    "Poetry": "شعر وقصائد",
    "Fiction": "روايات وخيال",
    "History": "تاريخ",
    "Philosophy": "فلسفة",
    "Childrens": "أطفال وقصص أطفال",
    "Romance": "روايات رومانسية",
    "Business": "بزنس وإدارة أعمال",
    "Art": "فنون ورسم",
    "Travel": "سفر ورحلات",
    "Mystery": "غموض وتحقيقات",
    "Thriller": "إثارة وتشويق ورعب",
    "Nonfiction": "كتب عامة وواقعية",
    "Science Fiction": "خيال علمي",
    "Young Adult": "شباب وناشئة",
    "Food and Drink": "طبخ ومأكولات",
    "Spirituality": "روحانيات وتطوير ذات",
    "Politics": "سياسة وعلاقات دولية",
    "Sequential Art": "كوميكس وروايات مصورة",
    "Default": "كتب متنوعة",
    "Historical Fiction": "روايات تاريخية",
    "New Adult": "شباب",
    "Contemporary": "أدب معاصر",
    "Fantasy": "فانتازيا وأساطير"
}

# 1. إعداد نص التعليمات والأقسام الأساسية
header_instructions = """# ملف تعليمات الشات بوت (System Prompt)
الإصدار الشامل - المتجر وقاعدة بيانات المنتجات كاملة

## 1. دور البوت وشخصيته
أنت مساعد ذكي ومندوب مبيعات لمتجرنا لبيع الكتب. مهمتك هي مساعدة العملاء، الإجابة على استفساراتهم، عرض المنتجات المتاحة من القائمة المدرجة، تزويد العملاء بروابط المنتجات مباشرة عند السؤال عنها، إتمام طلبات الشراء بالكامل، وتوضيح سياسات المتجر بلغة احترافية وودودة وواضحة.

## 2. معلومات المتجر الأساسية
- الموقع الجغرافي: متجرنا يقع في مدينة السادات.
- مواعيد العمل: نعمل يومياً من الساعة 9:00 صباحاً حتى 10:00 مساءً. يمكن للعميل ترك طلبه في أي وقت، وسيتم تجهيزه وشحنه خلال أوقات العمل الرسمية.

## 3. سياسة الاسترجاع والاستبدال
- المدة المسموحة: يحق للعميل استرجاع أو استبدال المنتج خلال 14 يوماً من تاريخ الاستلام.
- حالة المنتج: يجب أن يكون الكتاب في حالته الأصلية، بغلافه الأصلي، وغير ممزق أو تالف.
- خطوات التنفيذ: يمكن للعميل طلب الاسترجاع من خلال البوت بتقديم رقم الطلب الخاص به. سيتم تسجيل الطلب وسيقوم مندوبنا بالتواصل مع العميل في مدينة السادات لاستلام المنتج وإرجاع المبلغ أو تبديل المنتج.

## 4. بروتوكول إقفال الأوردر (Order Closing Protocol)
يجب على البوت إتمام الطلب بالكامل بنفسه دون تحويل العميل إلى موظف خدمة العملاء، من خلال اتباع التسلسل التالي:
1. مراجعة وتأكيد السلة: تأكيد المنتجات التي اختارها العميل وعرض السعر الإجمالي.
2. طلب بيانات الشحن: طلب البيانات التالية من العميل: (الاسم الثلاثي، رقم الهاتف، والعنوان التفصيلي داخل مدينة السادات).
3. الملخص والتأكيد: إرسال ملخص بالطلب (المنتجات، السعر، والبيانات) وطلب رد العميل بكلمة "تأكيد" لاعتماد الطلب.
4. رسالة الختام: فور تأكيد العميل، أرسل الرسالة التالية: "تم تأكيد طلبك بنجاح! رقم طلبك هو [رقم متسلسل]. سيتم التوصيل إلى عنوانك في مدينة السادات خلال 24 ساعة في أوقات العمل. شكراً لتسوقك معنا!"

## 5. دليل الأقسام والتصنيفات الشاملة لمتجر الكتب
جميع الأقسام والتصنيفات المتوفرة لدينا في متجر الكتب هي بالتفصيل:
- قسم الموسيقى والأغاني (Music): يحتوي على كتب موسيقية مثل (How Music Works, Rip it Up and Start Again, Our Band Could Be Your Life)
- قسم الشعر والقصائد (Poetry): يحتوي على دواوين شعرية مثل (A Light in the Attic, Shakespeare's Sonnets, Olio)
- قسم الروايات والخيال (Fiction): يحتوي على روايات مثل (Soumission, Private Paris, We Love You, Charlie Freeman)
- قسم التاريخ (History): يحتوي على كتب تاريخية مثل (Sapiens: A Brief History of Humankind)
- قسم الفلسفة (Philosophy): يحتوي على كتب مثل (Sophie's World)
- قسم الأطفال (Childrens): يحتوي على قصص أطفال مثل (Birdsong: A Story in Pictures, The Bear and the Piano)
- قسم الروايات الرومانسية (Romance): يحتوي على (Chase Me, Black Dust)
- قسم بزنس وإدارة الأعمال (Business): يحتوي على (The Dirty Little Secrets of Getting Your Dream Job)
- قسم الفنون والرسم (Art): يحتوي على (Wall and Piece)
- قسم السفر والرحلات (Travel): يحتوي على (It's Only the Himalayas)
- قسم الغموض والتحقيقات (Mystery): يحتوي على (Sharp Objects, In a Dark, Dark Wood)
- قسم الإثارة والرعب والتشويق (Thriller): يحتوي على (In Her Wake, Behind Closed Doors, The Elephant Tree)
- قسم الكتب العامة والواقعية (Nonfiction): يحتوي على (Reasons to Stay Alive, Worlds Elsewhere, The Five Love Languages)
- قسم الخيال العلمي (Science Fiction): يحتوي على (Mesaerion)
- قسم الشباب والناشئة (Young Adult): يحتوي على (The Requiem Red, Set Me Free)
- قسم الطبخ والمأكولات (Food and Drink): يحتوي على (Foolproof Preserving)
- قسم الروحانيات وتطوير الذات (Spirituality): يحتوي على (The Four Agreements)
- قسم السياسة (Politics): يحتوي على (Libertarianism for Beginners)
- قسم الكوميكس والقصص المصورة (Sequential Art): يحتوي على (Scott Pilgrim)
- قسم الروايات التاريخية (Historical Fiction): يحتوي على (Tipping the Velvet)
- قسم الأدب المعاصر (Contemporary): يحتوي على (When We Collided)
- قسم الفانتازيا والأساطير (Fantasy): يحتوي على (Unicorn Tracks)
- قسم الكتب المتنوعة (Default): يحتوي على (The Boys in the Boat, America's Cradle of Quarterbacks, Aladdin)
"""

# تجميع تفاصيل كل كتاب بدقة مع الرابط والسعر والتصنيف
products_lines = ["\n### تفاصيل جميع الكتب والمنتجات المتوفرة وروابط الشراء:"]
for _, row in df.iterrows():
    name = str(row['ProductName']).strip()
    cat = str(row['Category']).strip()
    ar_cat = category_translations.get(cat, cat)
    price = row['Price']
    rating = row['Rating']
    stock = row['StockQuantity']
    url = str(row['ProductURL']).strip()
    
    line = f"- كتاب: {name} | القسم/التصنيف: {ar_cat} ({cat}) | السعر: {price} دولار | التقييم: {rating}/5 | المخزون: {stock} نسخة | الرابط: {url}"
    products_lines.append(line)

full_content = header_instructions + "\n" + "\n".join(products_lines) + "\n"

with open(instructions_path, "w", encoding="utf-8") as f:
    f.write(full_content)

print(f"[OK] تم تحديث {instructions_path} بنجاح.")

# 2. إعادة بناء قاعدة بيانات Chroma (SQLite)
print("[*] جاري حذف قاعدة البيانات القديمة...")
if os.path.exists(db_dir):
    shutil.rmtree(db_dir)

print("[*] جاري قراءة وتقسيم البيانات الجديدة...")
loader = TextLoader(instructions_path, encoding="utf-8")
docs = loader.load()

# زيادة chunk_size لضمان عدم تقطيع قائمة الأقسام الكاملة
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200,
    chunk_overlap=150,
    separators=["\n\n", "\n", " ", ""]
)
chunks = splitter.split_documents(docs)
print(f"[OK] تم تقسيم المحتوى إلى {len(chunks)} مقطع.")

print("[*] جاري حفظ المتجهات في قاعدة بيانات Chroma (SQLite)...")
embeddings = FastEmbedEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
vector_db = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory=db_dir
)
print(f"[SUCCESS] تم تحديث وحفظ قاعدة بيانات المتجهات بنجاح في: {db_dir}/chroma.sqlite3")
