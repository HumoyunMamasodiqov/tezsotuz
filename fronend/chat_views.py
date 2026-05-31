from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.models import User 
from .models import Chat, Message, Mahsulot, SotibOlish
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.models import User  # <--- BU QATORNI QO'SHING
from .models import Chat, Message, Mahsulot, SotibOlish

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.models import User
from .models import Chat, Message, Mahsulot, SotibOlish


@login_required
def my_chats(request):
    chats = Chat.objects.filter(
        Q(buyer=request.user) | Q(seller=request.user)
    ).order_by('-updated_at')

    for chat in chats:
        chat.last_msg = chat.last_message()
        chat.unread = chat.unread_count(request.user)

    return render(request, 'my_chats.html', {'chats': chats})


@login_required
def chat_detail(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    if request.user not in [chat.buyer, chat.seller]:
        messages.error(request, "Siz bu chatga kira olmaysiz")
        return redirect('my_chats')

    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        image = request.FILES.get('image')
        if text or image:
            Message.objects.create(
                chat=chat,
                sender=request.user,
                text=text,
                image=image,
            )
            chat.save()
        return redirect('chat_detail', chat_id=chat.id)

    chat.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    messages_list = chat.messages.all()

    return render(request, 'chat_detail.html', {
        'chat': chat,
        'messages': messages_list,
        'other_user': chat.seller if request.user == chat.buyer else chat.buyer,
    })


@login_required
def start_chat(request, product_id, seller_id):
    mahsulot = get_object_or_404(Mahsulot, id=product_id)
    seller = get_object_or_404(User, id=seller_id)

    if request.user == seller:
        messages.warning(request, "O'zingiz bilan chat yarata olmaysiz")
        return redirect('mahsulot_detail', mahsulot_id=product_id)

    chat, created = Chat.objects.get_or_create(
        mahsulot=mahsulot,
        buyer=request.user,
        seller=seller,
    )
    return redirect('chat_detail', chat_id=chat.id)


@login_required
def api_send_message(request, chat_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST kerak'})

    chat = get_object_or_404(Chat, id=chat_id)
    if request.user not in [chat.buyer, chat.seller]:
        return JsonResponse({'success': False, 'error': 'Ruxsat yo\'q'})

    text = request.POST.get('text', '').strip()
    image = request.FILES.get('image')

    if not text and not image:
        return JsonResponse({'success': False, 'error': 'Xabar matni yoki rasm kerak'})

    msg = Message.objects.create(chat=chat, sender=request.user, text=text, image=image)
    chat.save()

    return JsonResponse({
        'success': True,
        'message': {
            'id': msg.id,
            'text': msg.text,
            'image': msg.image.url if msg.image else None,
            'created_at': msg.created_at.isoformat(),
            'is_mine': True,
        }
    })


@login_required
def api_chat_messages(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    if request.user not in [chat.buyer, chat.seller]:
        return JsonResponse({'success': False, 'error': 'Ruxsat yo\'q'})

    since = request.GET.get('since')
    messages_qs = chat.messages.all()
    if since:
        from django.utils.dateparse import parse_datetime
        dt = parse_datetime(since)
        if dt:
            messages_qs = messages_qs.filter(created_at__gt=dt)

    chat.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    return JsonResponse({
        'success': True,
        'messages': [{
            'id': m.id,
            'text': m.text,
            'image': m.image.url if m.image else None,
            'sender_id': m.sender.id,
            'is_mine': m.sender == request.user,
            'is_read': m.is_read,
            'created_at': m.created_at.isoformat(),
        } for m in messages_qs]
    })


@login_required
def api_unread_count(request):
    total_unread = Message.objects.filter(
        chat__in=Chat.objects.filter(Q(buyer=request.user) | Q(seller=request.user))
    ).exclude(sender=request.user).filter(is_read=False).count()

    return JsonResponse({'unread': total_unread})

@login_required
def chat_detail(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    if request.user not in [chat.buyer, chat.seller]:
        messages.error(request, "Siz bu chatga kira olmaysiz")
        return redirect('my_chats')

    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        image = request.FILES.get('image')
        if text or image:
            Message.objects.create(
                chat=chat,
                sender=request.user,
                text=text,
                image=image,
            )
            chat.save()
        return redirect('chat_detail', chat_id=chat.id)

    chat.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    messages_list = chat.messages.all()

    return render(request, 'chat_detail.html', {
        'chat': chat,
        'messages': messages_list,
        'other_user': chat.seller if request.user == chat.buyer else chat.buyer,
    })


@login_required
def start_chat(request, product_id, seller_id):
    mahsulot = get_object_or_404(Mahsulot, id=product_id)
    seller = get_object_or_404(User, id=seller_id)

    if request.user == seller:
        messages.warning(request, "O'zingiz bilan chat yarata olmaysiz")
        return redirect('mahsulot_detail', mahsulot_id=product_id)

    chat, created = Chat.objects.get_or_create(
        mahsulot=mahsulot,
        buyer=request.user,
        seller=seller,
    )
    return redirect('chat_detail', chat_id=chat.id)


@login_required
def api_send_message(request, chat_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST kerak'})

    chat = get_object_or_404(Chat, id=chat_id)
    if request.user not in [chat.buyer, chat.seller]:
        return JsonResponse({'success': False, 'error': 'Ruxsat yo\'q'})

    text = request.POST.get('text', '').strip()
    image = request.FILES.get('image')

    if not text and not image:
        return JsonResponse({'success': False, 'error': 'Xabar matni yoki rasm kerak'})

    msg = Message.objects.create(chat=chat, sender=request.user, text=text, image=image)
    chat.save()

    return JsonResponse({
        'success': True,
        'message': {
            'id': msg.id,
            'text': msg.text,
            'image': msg.image.url if msg.image else None,
            'created_at': msg.created_at.isoformat(),
            'is_mine': True,
        }
    })


@login_required
def api_chat_messages(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    if request.user not in [chat.buyer, chat.seller]:
        return JsonResponse({'success': False, 'error': 'Ruxsat yo\'q'})

    since = request.GET.get('since')
    messages_qs = chat.messages.all()
    if since:
        from django.utils.dateparse import parse_datetime
        dt = parse_datetime(since)
        if dt:
            messages_qs = messages_qs.filter(created_at__gt=dt)

    chat.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    return JsonResponse({
        'success': True,
        'messages': [{
            'id': m.id,
            'text': m.text,
            'image': m.image.url if m.image else None,
            'sender_id': m.sender.id,
            'is_mine': m.sender == request.user,
            'is_read': m.is_read,
            'created_at': m.created_at.isoformat(),
        } for m in messages_qs]
    })


@login_required
def api_unread_count(request):
    total_unread = Message.objects.filter(
        chat__in=Chat.objects.filter(Q(buyer=request.user) | Q(seller=request.user))
    ).exclude(sender=request.user).filter(is_read=False).count()

    return JsonResponse({'unread': total_unread})