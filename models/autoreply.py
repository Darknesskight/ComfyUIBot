class GuildAutoReply:
    def __init__(
            self,
            channel_id: str,
            prefix: str,
            reverse_check: bool
    ):
        super().__init__()
        self.channel_id = channel_id
        self.prefix = prefix or "!"
        self.reverse_check = reverse_check or False
