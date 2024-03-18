import atexit
import logging
from logging.handlers import QueueListener, QueueHandler
from queue import Queue

from disnake import SyncWebhook, Embed

from packages.config import Settings


class BotLogger:
    """
    Since Discord.py starts the bot into a single async thread, logging to i/o could block the thread.
    To prevent this a new thread is spawned that monitors for records in a logging queue.

    Basically the discord thread will just log into the queue and the listener will pick up any records
    and log them into i/o and web if needed.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.log_queue = Queue(-1)
        self.log_handlers = []

        # Set up webhook logger
        self._set_webhook_logging()

        # Set up terminal handler
        self._set_stdout_logging()

        root = logging.getLogger(self.settings.log_name)
        root.setLevel(settings.main_log_level)
        root.addHandler(QueueListenerHandler(self.log_handlers))

    def _set_webhook_logging(self):
        self.log_handlers.append(DiscordWebhookHandler(self.settings))

    def _set_stdout_logging(self):
        """Only log error leve and above to stdout for debugging"""
        logger_handler = logging.StreamHandler()
        formatter = logging.Formatter(self.settings.logging_format,
                                      "%d %b %H:%M:%S")
        logger_handler.setFormatter(formatter)
        logger_handler.setLevel(logging.ERROR)
        self.log_handlers.append(logger_handler)


class QueueListenerHandler(QueueHandler):
    """
    Fuse together the Queue Handler and Queue Listener. The Listener will get any logs since we are assigning it
    as the only log handler in "logging.getLogger".

    Since all logs must go to the Queue Listener then Queue Handler will then take them and emit them as normal
    in a new thread. So all normal handlers will go into Queue Handler instead of the root logger "logging.getLogger"
    """

    def __init__(self, handlers, respect_handler_level=True, auto_run=True,
                 queue=Queue(-1)):
        self.queue = queue
        super().__init__(self.queue)
        self._listener = QueueListener(
            self.queue,
            *handlers,
            respect_handler_level=respect_handler_level)
        if auto_run:
            self.start()
            atexit.register(self.stop)

    def start(self):
        self._listener.start()

    def stop(self):
        self._listener.stop()

    def emit(self, record):
        return super().emit(record)


class DiscordWebhookHandler(logging.Handler):
    """
    Logs to a discord webhook so that users can also see what is gong on
    """

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.webhook_url = self.settings.web_log_url
        self.setLevel(logging.DEBUG)

    def emit(self, record):
        try:
            self.discord_log(record)
        except Exception as error:
            logger = logging.getLogger('root')
            logger.error('Could not initialize web logger', exc_info=error)

    def discord_log(self, record: logging.LogRecord):
        colors = {
            10: 0xCCFFFF,  # Debug Cyan | Automatic tasks will go here
            20: 0x0B5394,  # Info  Blue | Changes by automatic tasks go here
            30: 0xFFD966,  # Warning    | User ran a command
            40: 0xFF0010,  # Error Org  | User caused an affect
            50: 0xFF0000  # Critical   | All errors will go here
        }
        webhook = SyncWebhook.from_url(self.webhook_url)

        if record.exc_info:
            msg = f"{record.msg}\n\n{record.exc_text}"
        else:
            msg = record.msg

        msgs = self.text_split(msg)
        embeds = []
        for msg in msgs:
            embeds.append(
                Embed(title=f"{record.name}\n{record.pathname.split('/')[-1]}:{record.lineno}\n\n",
                      description=f"{msg}",
                      color=colors[record.levelno]
                      )
            )

        embeds[-1].set_footer(text=f"Version: {self.settings.version}")
        webhook.send(embeds=embeds, username=self.settings.web_log_name)

    @staticmethod
    def text_split(text: str) -> list:
        blocks = []
        block = ""
        for i in text.split("\n"):
            if (len(i) + len(block)) > 1850:
                block = block.rstrip("\n")
                blocks.append(block)
                block = f"{i}\n"
            else:
                block += f"{i}\n"
        if block:
            blocks.append(block)
        return blocks
