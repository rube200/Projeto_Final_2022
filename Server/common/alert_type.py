from enum import Enum


class AlertType(Enum):
    Invalid = 0
    System = 1
    NewBell = 2
    Bell = 3
    Movement = 4
    UserPicture = 5
    OpenDoor = 6


def get_alert_type_message(alert: AlertType) -> str:
    if alert == AlertType.Invalid:
        return 'Invalid alert type'
    elif alert == AlertType.System:
        return 'System alert'
    elif alert == AlertType.NewBell:
        return 'New bell registered'
    elif alert == AlertType.Bell:
        return 'Doorbell pressed'
    elif alert == AlertType.Movement:
        return 'Motion detected'
    elif alert == AlertType.UserPicture:
        return 'User requested picture'
    elif alert == AlertType.OpenDoor:
        return 'User requested open door'
    else:
        return 'Unknown alert type'
