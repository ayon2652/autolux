from .models import ContactMessage, Favorite, TestDriveRequest


# Context processor global.
# Su función es inyectar en todas las plantillas ciertos contadores útiles
# para la navegación, como favoritos del usuario y mensajes pendientes del admin.
def admin_unread_contact_messages(request):
    """Añade al contexto contadores globales de favoritos y mensajes no leídos."""

    # Por defecto, si el usuario no ha iniciado sesión, no tendrá favoritos.
    favorite_count = 0

    # Si el usuario está autenticado, se calcula cuántos vehículos ha guardado en favoritos.
    if request.user.is_authenticated:
        favorite_count = Favorite.objects.filter(user=request.user).count()

    # Si además el usuario es personal del sistema (staff),
    # se calculan los mensajes de contacto y solicitudes de prueba pendientes de leer.
    if request.user.is_authenticated and request.user.is_staff:
        unread_contact_count = ContactMessage.objects.filter(is_read=False).count()
        unread_test_drive_count = TestDriveRequest.objects.filter(is_read=False).count()

        # Se devuelve el total de notificaciones pendientes junto al contador de favoritos.
        return {
            'admin_unread_messages_count': unread_contact_count + unread_test_drive_count,
            'favorite_count': favorite_count,
        }

    # Para usuarios normales o visitantes, solo se devuelve el contador de favoritos
    # y el número de mensajes pendientes del panel admin queda a cero.
    return {
        'admin_unread_messages_count': 0,
        'favorite_count': favorite_count,
    }
