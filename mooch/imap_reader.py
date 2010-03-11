import datetime
import base64
import email
import email.header
import imaplib
import StringIO

from django.conf import settings
from django.contrib.auth.models import User

from mooch.logging.models import LogEntry, LogEntryFile


class IMAPReader(object):
    def __init__(self):
        self.client = imaplib.IMAP4_SSL(settings.IMAP_HOST)
        self.client.login(settings.IMAP_USERNAME, settings.IMAP_PASSWORD)
        self.client.select('INBOX')

    def unread_messages(self):
        return self.client.search(None, 'UNSEEN')[1][0].split()

    def mark_seen(self, message):
        return self.client.store(message, '+FLAGS', r'\Seen')

    def fetch(self, message):
        return email.message_from_string(self.client.fetch(message, '(RFC822)')[1][0][1])

    def fetch_and_save_unseen(self):
        def handler(entry, files, msg):
            """
            Recursively parse multipart mails
            """

            if msg.is_multipart():
                for part in msg.get_payload():
                    handler(entry, files, part)
                return

            if msg.get_content_maintype() == 'text':
                entry.message += msg.get_payload().decode(msg.get_content_charset())
            elif msg.get_content_maintype() in ('image', 'application'):
                files.append((
                    msg.get_filename(), # filename
                    msg.get_filename(), # title
                    msg.get_content_type(),
                    base64.decodestring(msg.get_payload()),
                    ))
            else:
                print 'Cannot handle type %s yet' % msg.get_content_type()

        def decode_header(header):
            value = email.header.decode_header(header)
            if value[0][1]:
                return value[0][0].decode(value[0][1])
            return value[0][0]

        entries = []
        for msgid in self.unread_messages():
            entry = LogEntry(account=User.objects.all()[0], source='EML')
            files = []

            msg = self.fetch(msgid)
            handler(entry, files, msg)

            for key, value in msg.items():
                if key == 'Subject':
                    entry.title = decode_header(value)
                elif key == 'Date':
                    entry.reported = datetime.datetime(*email.utils.parsedate(value)[:7])
                elif key == 'From':
                    entry.source_detail = decode_header(value)

            if not entry.title:
                entry.title = entry.message[:100]

            entry.save()

            from django.core.files.uploadedfile import InMemoryUploadedFile

            for filename, title, contenttype, data in files:
                f = LogEntryFile(
                    logentry=entry,
                    title=title,
                    )
                f_obj = InMemoryUploadedFile(
                    StringIO.StringIO(data),
                    'file',
                    filename,
                    contenttype,
                    len(data),
                    'utf-8',
                    )
                f.file.save(filename, f_obj)
                f.save()

            self.mark_seen(msgid)
            entries.append(entry)

        return entries
