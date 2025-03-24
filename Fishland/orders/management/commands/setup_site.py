from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site

class Command(BaseCommand):
    help = 'Set up the default site domain'

    def handle(self, *args, **kwargs):
        site = Site.objects.get(id=1)
        site.domain = 'fishland.com'
        site.name = 'FISHLAND'
        site.save()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully set up site domain to fishland.com')
        )
