from django.contrib.auth.models import User
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import Profile


@receiver(post_migrate)
def create_default_users(sender, **kwargs):
    try:
        # Create Owner
        if not User.objects.filter(username='owner').exists():
            owner = User.objects.create_user(username='owner', password='Owner@123')
            Profile.objects.create(user=owner, role='owner')
            owner.is_staff = True
            owner.is_superuser = True
            owner.save()
            # print("Owner user created.")
        # else:
        #     print("Owner user already exists.")

        # Create Customer
        if not User.objects.filter(username='customer').exists():
            customer = User.objects.create_user(username='customer', password='Customer@123')
            Profile.objects.create(user=customer, role='customer')
            # print("Customer user created.")
        # else:
        #     print("Customer user already exists.")

        # Create Supplier
        if not User.objects.filter(username='supplier').exists():
            supplier = User.objects.create_user(username='supplier', password='Supplier@123')
            Profile.objects.create(user=supplier, role='supplier')
            # print("Supplier user created.")
        # else:
        #     print("Supplier user already exists.")

    except Exception as e:
        print(f"Error creating default users: {e}")
