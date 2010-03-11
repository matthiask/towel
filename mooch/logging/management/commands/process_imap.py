from django.core.management.base import NoArgsCommand

from mooch.imap_reader import IMAPReader


class Command(NoArgsCommand):
    help = '''Processes IMAP'''

    def handle(self, **options):
        i = IMAPReader()
        print i.fetch_and_save_unseen()
        i.client.shutdown()
