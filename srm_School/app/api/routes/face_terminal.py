from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.database import get_db
from app.models.device import Device
from app.models.student import Student
from app.models.attendance import Attendance
from datetime import datetime, time
import json
import logging

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/face-terminal", tags=["Face Terminal"])

@router.post("/log")
async def receive_log(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        content_type = request.headers.get("Content-Type")
        body = await request.body()

        if content_type.startswith("multipart/form-data"):
            form_data = await request.form()
            raw_json = form_data.get("AccessControllerEvent")
            if not raw_json:
                raise HTTPException(status_code=400, detail="AccessControllerEvent not found")
            data = json.loads(raw_json)
        else:
            raise HTTPException(status_code=400, detail="Unsupported Content-Type")

        event = data.get("AccessControllerEvent", data)
        event_type = data.get("eventType", event.get("eventType"))
        if event_type != "AccessControllerEvent":
            return {"message": f"eventType noto‘g‘ri: {event_type}"}

        sub_event_type = event.get("subEventType")
        if sub_event_type != 75:
            return {"message": f"subEventType = {sub_event_type}, not authentication event"}

        employee_id_str = event.get("employeeNoString")
        if not employee_id_str:
            return {"message": "⚠️ employeeNoString topilmadi"}

        face_terminal_id = int(employee_id_str)

        result = await db.execute(select(Student).where(Student.face_terminal_id == face_terminal_id))
        student = result.scalar_one_or_none()
        if not student:
            raise HTTPException(status_code=404, detail="Student topilmadi")

        dt_str = data.get("dateTime")
        dt = datetime.fromisoformat(dt_str)
        date_part = dt.date()
        time_part = dt.time()

        # Kechikish hisobi
        late_threshold = time(17, 0)
        if time_part > late_threshold:
            delta = datetime.combine(date_part, time_part) - datetime.combine(date_part, late_threshold)
            late_minutes = int(delta.total_seconds() // 60)
            status = "late"
        else:
            late_minutes = 0
            status = "on_time"

        device_serial = data.get("shortSerialNumber")
        result = await db.execute(select(Device).where(Device.serial_number == device_serial))
        device = result.scalar_one_or_none()
        if not device:
            raise HTTPException(status_code=404, detail="Qurilma topilmadi")

        # Davomat yozuvi
        attendance = Attendance(
            student_id=student.id,
            date=date_part,
            arrival_time=time_part,
            late_minutes=late_minutes,
            is_present=True,
            event_type=event.get("majorEventType"),
            sub_event_type=sub_event_type,
            user_type=event.get("userType", "unknown"),
            serial_no=str(event.get("serialNo")),
            device_name=event.get("deviceName"),
            school_id=student.school_id
        )
        db.add(attendance)
        await db.commit()

        logger.info({
            "message": "✅ Davomat yozildi",
            "student_id": student.id,
            "full_name": f"{student.first_name} {student.last_name}",
            "arrival_time": time_part.strftime("%H:%M:%S"),
            "status": status,
            "late_minutes": late_minutes
        })

        return {
            "message": "✅ Davomat yozildi",
            "student_id": student.id,
            "arrival_time": time_part.strftime("%H:%M:%S"),
            "status": status,
            "late_minutes": late_minutes
        }

    except Exception as e:
        logger.exception("❌ Xatolik yuz berdi")
        raise HTTPException(status_code=400, detail=f"Xatolik: {str(e)}")
