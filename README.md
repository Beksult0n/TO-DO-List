# 🧠 PyQt5 yordamida TO-DO List yaratish
Bu loyiha — PyQt5 yordamida yaratilgan **sodda, chiroyli va qulay desktop planner (TODO app)**.  
U kundalik vazifalarni boshqarish, vaqtni rejalashtirish va fokusni oshirish uchun mo‘ljallangan.

---

## ✨ Asosiy imkoniyatlar

### 📅 Vazifalar boshqaruvi
- Vazifa qo‘shish, tahrirlash va o‘chirish
- Vazifalarni **sana bo‘yicha saqlash**
- Har bir vazifaga **kategoriya berish**
- **Deadline (vaqt)** qo‘shish
- Vazifani bajarildi deb belgilash

---

### 🔍 Qidiruv va filter
- Vazifalarni tez qidirish (search)
- Filterlash:
  - Barchasi (All)
  - Bajarilmagan (Pending)
  - Bajarilgan (Completed)

---

### ⏱️ Pomodoro Timer
- Ishlash vaqti sozlanadi
- Start / Pause / Reset
- Fokusni oshirish uchun qulay vosita

---

### 🌙 Dizayn
- Zamonaviy minimalistik UI
- Light mode / Dark mode
- Real vaqt (clock) ko‘rsatiladi

---

### 📤 Export
- Vazifalarni **CSV** formatda saqlash
- Vazifalarni **PDF** formatda eksport qilish

---

## 🖼️ Skrinshotlar

### Light Mode
![Light Mode](light.png)

### Dark Mode
![Dark Mode](dark.png)


---

## ⚙️ O‘rnatish

### 1. Loyihani yuklab olish

```bash
git clone https://github.com/Beksult0n/TO-DO-List.git
cd TO-DO-List
```
## Kerakli kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```
## .EXE fayl sifatida o'rnatish
```bash
python -m PyInstaller --noconfirm --onefile --windowed --name "TO-DO_List" --icon "icon.png" --add-data "todo.ui;." todo.py
```


