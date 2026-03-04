# 3Frame_Plot

แอปเดสก์ท็อปสำหรับดูข้อมูล C-Scan แบบ 3 เฟรม (Tkinter + Matplotlib) รองรับการนำเข้าไฟล์ Excel หลายชีต, ปรับสเกลสี, และส่งออกเฟรมปัจจุบันเป็น Excel

## วิธีติดตั้ง

1. ใช้ Python 3.10+ (แนะนำ)
2. ติดตั้ง dependencies:

```bash
pip install -r requirements.txt
```

## วิธีรันโปรแกรม

รันแบบปกติ:

```bash
python cscan_viewer.py
```


## วิธีใช้งานเบื้องต้น

1. เปิดโปรแกรม
2. กดปุ่ม Import Excel เพื่อเลือกไฟล์ `.xlsx` / `.xls`
3. เลือกชีตสำหรับ Frame A / Frame B / Frame C
4. ปรับค่าสี (Colormap) และช่วงสเกล (Min/Max) ตามต้องการ
5. ใช้แถบ preview ด้านล่างเพื่อเลื่อน/ซูมช่วงข้อมูลแนวนอน
6. กด Export เพื่อบันทึกเฟรมปัจจุบันเป็นไฟล์ Excel

## ไฟล์สำคัญ

- `cscan_viewer.py` : จุดเริ่มต้นของแอป (GUI หลัก)
- `cscan_app/` : โมดูลย่อยสำหรับ layout, data processing, และ colormap
- `requirements.txt` : รายการแพ็กเกจที่จำเป็น

