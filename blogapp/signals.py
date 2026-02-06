from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import *


@receiver(post_save, sender=Blog)
def send_blog_notification(sender, instance, created, **kwargs):
    if created:  # Only when a new blog is created
        subscribers = Subscriber.objects.all()
        recipient_list = [sub.email for sub in subscribers]

        if recipient_list:
            send_mail(
                subject=f"New Blog Post: {instance.title}",
                message=f"A new blog post has been published!\n\n{instance.title}\n\n{instance.content[:200]}...",
                from_email=None,  # Uses DEFAULT_FROM_EMAIL
                recipient_list=recipient_list,
                fail_silently=False,
            )