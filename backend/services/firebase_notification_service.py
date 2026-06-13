"""
Firebase Cloud Messaging notification service.
Gracefully degrades to console logging if Firebase is not configured.
"""

import logging
import os

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Firebase Admin SDK initialisation
# Set FIREBASE_CREDENTIALS_PATH in .env to point to your service account JSON.
# Without it, notifications are simulated (logged only).
# ---------------------------------------------------------------------------

_firebase_initialized = False
_messaging = None

def _init_firebase():
    global _firebase_initialized, _messaging
    if _firebase_initialized:
        return

    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
    if not cred_path or not os.path.exists(cred_path):
        logger.warning(
            "Firebase not configured. Notifications will be logged only. "
            "Set FIREBASE_CREDENTIALS_PATH in .env to enable real FCM."
        )
        _firebase_initialized = True
        return

    try:
        import firebase_admin
        from firebase_admin import credentials, messaging as fcm_messaging

        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)

        _messaging = fcm_messaging
        _firebase_initialized = True
        logger.info("Firebase Admin SDK initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        _firebase_initialized = True


def send_notification(topic: str, title: str, body: str, data: dict = None) -> bool:
    """
    Send an FCM notification to a topic.

    Topics:
      - 'staff'   — all staff members
      - 'patient_{patient_id}'  — specific patient
      - 'doctor_{doctor_id}'    — specific doctor

    Returns True if sent successfully, False otherwise.
    """
    _init_firebase()

    log_msg = f"[FCM] Topic={topic!r} | {title} — {body}"

    if _messaging is None:
        # Simulated mode
        logger.info(f"[SIMULATED] {log_msg}")
        # Safely print to console for Windows
        safe_log = log_msg.encode('ascii', 'replace').decode('ascii')
        print(f"NOTIF: {safe_log}")
        return True

    try:
        message = _messaging.Message(
            notification=_messaging.Notification(title=title, body=body),
            data=data or {},
            topic=topic,
        )
        response = _messaging.send(message)
        logger.info(f"FCM sent. Response: {response} | {log_msg}")
        return True
    except Exception as e:
        logger.error(f"FCM send failed: {e} | {log_msg}")
        return False


# ---------------------------------------------------------------------------
# Convenience helpers — domain-specific events
# ---------------------------------------------------------------------------

def notify_staff_new_appointment(patient_name: str, appointment_id: str):
    """Notify all staff when a patient books an appointment."""
    send_notification(
        topic="staff",
        title="📅 New Appointment Request",
        body=f"{patient_name} has booked an appointment. Please review and approve.",
        data={"type": "new_appointment", "appointment_id": appointment_id},
    )


def notify_patient_appointment_approved(patient_id: str, doctor_name: str, date: str):
    """Notify patient when their appointment is approved."""
    send_notification(
        topic=f"patient_{patient_id}",
        title="✅ Appointment Approved",
        body=f"Your appointment with {doctor_name} on {date} has been approved.",
        data={"type": "appointment_approved"},
    )


def notify_patient_appointment_rejected(patient_id: str):
    """Notify patient when their appointment is rejected."""
    send_notification(
        topic=f"patient_{patient_id}",
        title="❌ Appointment Not Approved",
        body="Your appointment request was not approved. Please contact the hospital for details.",
        data={"type": "appointment_rejected"},
    )


def notify_doctor_new_appointment(doctor_id: str, patient_name: str, date: str):
    """Notify doctor when an appointment is assigned to them."""
    send_notification(
        topic=f"doctor_{doctor_id}",
        title="🩺 New Patient Appointment",
        body=f"New patient appointment assigned: {patient_name} on {date}.",
        data={"type": "appointment_assigned"},
    )


def notify_patient_prescription_ready(patient_id: str, doctor_name: str):
    """Notify patient when a prescription is created."""
    send_notification(
        topic=f"patient_{patient_id}",
        title="💊 Prescription Ready",
        body=f"Dr. {doctor_name} has created a new prescription for you.",
        data={"type": "prescription_ready"},
    )
