# app/services/sms_templates.py

def _fio(student) -> str:
    return f"{(student.first_name or '').strip()} {(student.last_name or '').strip()}".strip()

def sms_keldi(student, soat: str) -> str:
    ism = _fio(student)
    return (
        f"Bu Eskiz dan test"
    )

def sms_kechikib_keldi(student, daqiqa: int) -> str:
    ism = _fio(student)
    return (
        f"Bu Eskiz dan test"
    )

def sms_ketdi(student, soat: str) -> str:
    ism = _fio(student)
    return (
        f"Bu Eskiz dan test"
    )

def sms_kelmagan(student) -> str:
    ism = _fio(student)
    return (
        f"Bu Eskiz dan test"
    )

# app/services/sms_templates.py

# def _fio(student) -> str:
#     return f"{(student.first_name or '').strip()} {(student.last_name or '').strip()}".strip()

# def sms_keldi(student, soat: str) -> str:
#     ism = _fio(student)
#     return (
#         "📌 O‘quvchi davomati (Face ID asosida)\n"
#         "1. Keldi\n"
#         f"Hurmatli ota-ona, farzandingiz {ism} bugun {soat} da maktabga tashrif buyurdi (Face ID orqali qayd etildi)."
#     )

# def sms_kechikib_keldi(student, daqiqa: int) -> str:
#     ism = _fio(student)
#     return (
#         "📌 O‘quvchi davomati (Face ID asosida)\n"
#         "3. Darsga kechikib keldi\n"
#         f"Farzandingiz {ism} darsga {daqiqa} daqiqa kechikib keldi. Iltimos, e’tibor bering."
#     )

# def sms_ketdi(student, soat: str) -> str:
#     ism = _fio(student)
#     return (
#         "📌 O‘quvchi davomati (Face ID asosida)\n"
#         "2. Ketdi\n"
#         f"Farzandingiz {ism} bugun {soat} da maktabdan chiqdi (Face ID orqali qayd etildi)."
#     )

# def sms_kelmagan(student) -> str:
#     ism = _fio(student)
#     return (
#         "📌 O‘quvchi davomati (Face ID asosida)\n"
#         "4. Kelmadi\n"
#         f"Bugun farzandingiz {ism} maktabga tashrif buyurmadi. Iltimos, sababini ma’muriyatga xabar bering."
#     )
