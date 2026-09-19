# -*- coding: utf-8 -*-
"""
نظام إدارة الصيدلية - نسخة Python باستخدام Streamlit + SQLite
تشغيل:
  pip install streamlit pandas
  streamlit run app.py
"""
import sqlite3
from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st

DB = "pharmacy.db"
st.set_page_config(page_title="شركة الرواد للأدوية", page_icon="💊", layout="wide")

# ألوان قريبة من التصميم الأصلي
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
html, body, [class*="css"] {font-family:'Cairo',sans-serif; direction:rtl;}
[data-testid="stSidebar"] {background:#1f3b3a;}
[data-testid="stSidebar"] * {color:#fff !important;}
.stApp {background:#f5f7f4;}
div[data-testid="stMetric"] {background:white;border:1px solid #dce5dc;padding:14px;border-radius:12px;}
div.stButton>button {border-radius:8px;font-weight:600;}
</style>
""", unsafe_allow_html=True)

def connect():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS medicines(
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT,
          batch TEXT, quantity INTEGER DEFAULT 0, unit TEXT, unit_price REAL DEFAULT 0,
          expiry_date TEXT, min_stock INTEGER DEFAULT 10, supplier_id INTEGER);
        CREATE TABLE IF NOT EXISTS suppliers(
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT, email TEXT, address TEXT);
        CREATE TABLE IF NOT EXISTS sales(
          id INTEGER PRIMARY KEY AUTOINCREMENT, sale_date TEXT, customer TEXT, medicine_id INTEGER,
          qty INTEGER, unit_price REAL, total REAL);
        CREATE TABLE IF NOT EXISTS purchases(
          id INTEGER PRIMARY KEY AUTOINCREMENT, purchase_date TEXT, supplier_id INTEGER,
          medicine_id INTEGER, qty INTEGER, unit_cost REAL, total REAL);
        """)
        if c.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0] == 0:
            c.executemany("INSERT INTO suppliers(name,phone,email,address) VALUES(?,?,?,?)", [
                ("شركة الشفاء للتوزيع","0910000001","info@shifa.example","الخرطوم"),
                ("مؤسسة النيل الطبية","0910000002","sales@nile.example","أم درمان"),
                ("المتحدة للأدوية","0910000003","","بحري")])
        if c.execute("SELECT COUNT(*) FROM medicines").fetchone()[0] == 0:
            c.executemany("""INSERT INTO medicines(name,category,batch,quantity,unit,unit_price,expiry_date,min_stock,supplier_id)
            VALUES(?,?,?,?,?,?,?,?,?)""", [
                ("باراسيتامول 500 مجم","مسكنات","B-1001",120,"علبة",12.5,(date.today()+timedelta(days=400)).isoformat(),20,1),
                ("أموكسيسيلين 500 مجم","مضادات حيوية","B-1002",35,"علبة",34,(date.today()+timedelta(days=250)).isoformat(),15,2),
                ("فيتامين C","فيتامينات","B-1003",8,"علبة",22,(date.today()+timedelta(days=50)).isoformat(),10,3),
                ("شراب كحة","أدوية عامة","B-1004",60,"زجاجة",38,(date.today()+timedelta(days=700)).isoformat(),12,1)])
init_db()

def df(query, params=()):
    with connect() as c:
        return pd.read_sql_query(query, c, params=params)

def run(query, params=()):
    with connect() as c:
        c.execute(query, params)
        c.commit()

def money(x):
    return f"{float(x or 0):,.2f} ج.س"

st.sidebar.markdown("## 💊 شركة الرواد للأدوية")
st.sidebar.caption("نظام إدارة المخزون والمبيعات")
page = st.sidebar.radio("القائمة الرئيسية", ["لوحة القيادة","المخزون","المبيعات","الموردون والمشتريات","التقارير"])
today = date.today().isoformat()

meds = df("SELECT * FROM medicines")
suppliers = df("SELECT * FROM suppliers")
sales = df("SELECT * FROM sales")
purchases = df("SELECT * FROM purchases")
expiry = pd.to_datetime(meds["expiry_date"], errors="coerce") if not meds.empty else pd.Series(dtype="datetime64[ns]")
low_count = int((meds["quantity"] <= meds["min_stock"]).sum()) if not meds.empty else 0
expired_count = int((expiry.dt.date < date.today()).sum()) if not meds.empty else 0
near_count = int(((expiry.dt.date >= date.today()) & (expiry.dt.date <= date.today()+timedelta(days=90))).sum()) if not meds.empty else 0
today_sales = float(sales.loc[sales["sale_date"] == today, "total"].sum()) if not sales.empty else 0
stock_value = float((meds["quantity"] * meds["unit_price"]).sum()) if not meds.empty else 0

def metric_row():
    a,b,c,d = st.columns(4)
    a.metric("قيمة المخزون", money(stock_value))
    b.metric("مبيعات اليوم", money(today_sales))
    c.metric("أصناف منخفضة", low_count)
    d.metric("قرب الانتهاء / منتهي", f"{near_count} / {expired_count}")

if page == "لوحة القيادة":
    st.title("لوحة القيادة")
    st.caption(f"ملخص الصيدلية — {date.today().strftime('%Y-%m-%d')}")
    metric_row()
    left,right = st.columns(2)
    with left:
        st.subheader("الأدوية منخفضة المخزون")
        low = meds[meds["quantity"] <= meds["min_stock"]] if not meds.empty else meds
        st.dataframe(low[["name","quantity","min_stock","expiry_date"]] if not low.empty else pd.DataFrame(columns=["name","quantity","min_stock","expiry_date"]), use_container_width=True, hide_index=True)
    with right:
        st.subheader("آخر المبيعات")
        st.dataframe(sales.sort_values("id",ascending=False).head(8), use_container_width=True, hide_index=True)
    st.subheader("تنبيهات الصلاحية")
    if not meds.empty:
        alerts = meds[(pd.to_datetime(meds.expiry_date,errors="coerce") <= pd.Timestamp(date.today()+timedelta(days=90)))]
        st.dataframe(alerts[["name","batch","quantity","expiry_date"]] if not alerts.empty else pd.DataFrame(columns=["name","batch","quantity","expiry_date"]), use_container_width=True, hide_index=True)

elif page == "المخزون":
    st.title("إدارة المخزون")
    with st.expander("➕ إضافة دواء جديد", expanded=False):
        with st.form("new_med"):
            name=st.text_input("اسم الدواء*")
            category=st.selectbox("الفئة",["مسكنات","مضادات حيوية","فيتامينات","أدوية عامة","أدوية مزمنة","أخرى"])
            batch=st.text_input("رقم التشغيلة")
            q=st.number_input("الكمية",min_value=0,step=1)
            unit=st.selectbox("الوحدة",["علبة","شريط","زجاجة","قطعة","كرتونة"])
            price=st.number_input("سعر الوحدة",min_value=0.0,step=1.0)
            exp=st.date_input("تاريخ الانتهاء",value=date.today()+timedelta(days=365))
            minimum=st.number_input("الحد الأدنى للمخزون",min_value=0,value=10,step=1)
            supplier=st.selectbox("المورد", options=[(int(r.id),r["name"]) for _,r in suppliers.iterrows()], format_func=lambda x:x[1]) if not suppliers.empty else None
            submitted=st.form_submit_button("حفظ الدواء")
            if submitted:
                if not name.strip(): st.error("يرجى إدخال اسم الدواء.")
                else:
                    run("""INSERT INTO medicines(name,category,batch,quantity,unit,unit_price,expiry_date,min_stock,supplier_id)
                    VALUES(?,?,?,?,?,?,?,?,?)""",(name,category,batch,int(q),unit,float(price),exp.isoformat(),int(minimum),supplier[0] if supplier else None))
                    st.success("تمت إضافة الدواء."); st.rerun()
    search=st.text_input("ابحث باسم الدواء أو التشغيلة")
    view=meds.copy()
    if search: view=view[view.name.str.contains(search,case=False,na=False) | view.batch.str.contains(search,case=False,na=False)]
    st.dataframe(view, use_container_width=True, hide_index=True)
    st.subheader("تعديل كمية أو سعر")
    if not meds.empty:
        chosen=st.selectbox("اختر الدواء", options=meds.id.tolist(), format_func=lambda x: meds.loc[meds.id==x,"name"].iloc[0])
        row=meds[meds.id==chosen].iloc[0]
        with st.form("edit_med"):
            nq=st.number_input("الكمية الجديدة",min_value=0,value=int(row.quantity),step=1)
            np=st.number_input("سعر الوحدة الجديد",min_value=0.0,value=float(row.unit_price),step=1.0)
            save=st.form_submit_button("تحديث")
            if save:
                run("UPDATE medicines SET quantity=?,unit_price=? WHERE id=?",(int(nq),float(np),int(chosen)))
                st.success("تم التحديث."); st.rerun()
        if st.button("حذف الدواء المحدد"):
            run("DELETE FROM medicines WHERE id=?",(int(chosen),)); st.rerun()

elif page == "المبيعات":
    st.title("تسجيل المبيعات")
    if meds.empty:
        st.info("أضف أدوية للمخزون أولاً.")
    else:
        with st.form("sale_form"):
            customer=st.text_input("اسم العميل",value="عميل نقدي")
            mid=st.selectbox("الدواء",options=meds.id.tolist(),format_func=lambda x: meds.loc[meds.id==x,"name"].iloc[0])
            mr=meds[meds.id==mid].iloc[0]
            st.caption(f"المتوفر: {int(mr.quantity)} {mr.unit} — سعر الوحدة: {money(mr.unit_price)}")
            qty=st.number_input("الكمية",min_value=1,max_value=max(1,int(mr.quantity)),value=1,step=1)
            unit_price=st.number_input("سعر البيع للوحدة",min_value=0.0,value=float(mr.unit_price),step=1.0)
            st.write("الإجمالي:",money(qty*unit_price))
            submit=st.form_submit_button("إتمام البيع")
            if submit:
                if qty>mr.quantity: st.error("الكمية المطلوبة أكبر من المتوفر.")
                else:
                    run("INSERT INTO sales(sale_date,customer,medicine_id,qty,unit_price,total) VALUES(?,?,?,?,?,?)",
                        (today,customer,int(mid),int(qty),float(unit_price),float(qty*unit_price)))
                    run("UPDATE medicines SET quantity=quantity-? WHERE id=?",(int(qty),int(mid)))
                    st.success("تم تسجيل البيع وتحديث المخزون."); st.rerun()
    st.subheader("سجل المبيعات")
    st.dataframe(df("""SELECT s.id,s.sale_date,s.customer,m.name AS medicine,s.qty,s.unit_price,s.total
    FROM sales s LEFT JOIN medicines m ON m.id=s.medicine_id ORDER BY s.id DESC"""),use_container_width=True,hide_index=True)

elif page == "الموردون والمشتريات":
    st.title("الموردون والمشتريات")
    st.subheader("الموردون")
    with st.expander("➕ إضافة مورد"):
        with st.form("supplier_form"):
            sn=st.text_input("اسم المورد*"); phone=st.text_input("الهاتف"); email=st.text_input("البريد الإلكتروني"); address=st.text_input("العنوان")
            add=st.form_submit_button("حفظ المورد")
            if add:
                if sn.strip():
                    run("INSERT INTO suppliers(name,phone,email,address) VALUES(?,?,?,?)",(sn,phone,email,address)); st.rerun()
                else: st.error("اسم المورد مطلوب.")
    st.dataframe(suppliers,use_container_width=True,hide_index=True)
    st.subheader("تسجيل مشتريات")
    if not meds.empty and not suppliers.empty:
        with st.form("purchase_form"):
            sup=st.selectbox("المورد",options=suppliers.id.tolist(),format_func=lambda x:suppliers.loc[suppliers.id==x,"name"].iloc[0])
            mid=st.selectbox("الدواء المستلم",options=meds.id.tolist(),format_func=lambda x:meds.loc[meds.id==x,"name"].iloc[0])
            qty=st.number_input("الكمية المستلمة",min_value=1,value=1,step=1)
            cost=st.number_input("تكلفة الوحدة",min_value=0.0,step=1.0)
            save=st.form_submit_button("تسجيل المشتريات")
            if save:
                run("INSERT INTO purchases(purchase_date,supplier_id,medicine_id,qty,unit_cost,total) VALUES(?,?,?,?,?,?)",(today,int(sup),int(mid),int(qty),float(cost),qty*cost))
                run("UPDATE medicines SET quantity=quantity+? WHERE id=?",(int(qty),int(mid)))
                st.success("تم تسجيل المشتريات وزيادة المخزون."); st.rerun()
    st.subheader("سجل أوامر الشراء")
    st.dataframe(df("""SELECT p.id,p.purchase_date,s.name AS supplier,m.name AS medicine,p.qty,p.unit_cost,p.total
    FROM purchases p LEFT JOIN suppliers s ON s.id=p.supplier_id LEFT JOIN medicines m ON m.id=p.medicine_id ORDER BY p.id DESC"""),use_container_width=True,hide_index=True)

elif page == "التقارير":
    st.title("التقارير")
    metric_row()
    st.subheader("تقرير المخزون")
    st.dataframe(meds,use_container_width=True,hide_index=True)
    st.subheader("ملخص المبيعات حسب التاريخ")
    if not sales.empty:
        summary=sales.groupby("sale_date",as_index=False).agg(عدد_العمليات=("id","count"),إجمالي_المبيعات=("total","sum"))
        st.dataframe(summary.sort_values("sale_date",ascending=False),use_container_width=True,hide_index=True)
        st.download_button("تنزيل تقرير المبيعات CSV",sales.to_csv(index=False).encode("utf-8-sig"),"sales_report.csv","text/csv")
    else: st.info("لا توجد مبيعات مسجلة حتى الآن.")
    st.subheader("تنزيل بيانات المخزون")
    st.download_button("تنزيل المخزون CSV",meds.to_csv(index=False).encode("utf-8-sig"),"inventory.csv","text/csv")

st.sidebar.divider()
st.sidebar.caption("نسخة أولية — احرص على النسخ الاحتياطي لملف pharmacy.db")
