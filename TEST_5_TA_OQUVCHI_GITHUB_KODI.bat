@echo off
chcp 65001 >nul
title GITHUB PIPELINE - 5 TA O'QUVCHINI TEST QILISH
color 0B
echo ======================================================================
echo    GITHUB PIPELINE: 5 TA O'QUVCHI UCHUN TO'LIQ BOSQICHLAR
echo    1. Aileaders.uz da ro'yxatdan o'tish
echo    2. Aktivatsiya xatini ochish
echo    3. Aileaders da kursni TEKSHIRISH (Coursera taklifnomasini jo'natish)
echo    4. Coursera Join now taklifnomasini qabul qilish
echo    5. Testlarni 100%% yechib sertifikat olish
echo ======================================================================
cd /d "D:\uzbekcodersbot"
"C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe" run_5_students_test.py
pause
