"""Discord channel: /sprawdz, /usun_moje_dane, DMs and @mentions → POST /v1/checks."""

import logging
import re

import discord
from discord import app_commands

from prawdowid_discord.api import ApiUnavailableError, PrawdowidClient, get_check_input
from prawdowid_discord.config import get_settings
from prawdowid_discord.render import get_result_embeds, get_status_embed, get_unavailable_embed

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 5 * 1024 * 1024
HELP_TEXT = (
    "Wyślij mi treść, link albo zrzut ekranu, a sprawdzę je w oficjalnych źródłach. "
    "Możesz też użyć komendy `/sprawdz`. Zawsze pokazuję dosłowne cytaty i mówię, gdy nie wiem."
)


class PrawdowidBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.settings = get_settings()
        self.api = PrawdowidClient(self.settings.prawdowid_api_url, self.settings.api_timeout_s)
        self.tree = app_commands.CommandTree(self)
        self._register_commands()

    def _register_commands(self) -> None:
        @self.tree.command(name="sprawdz", description="Sprawdź informację w oficjalnych źródłach")
        @app_commands.allowed_installs(guilds=True, users=True)
        @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
        @app_commands.describe(tresc="Treść albo link do sprawdzenia", obraz="Zrzut ekranu (opcjonalnie)")
        async def check_command(
            interaction: discord.Interaction, tresc: str | None = None, obraz: discord.Attachment | None = None
        ) -> None:
            await interaction.response.defer(thinking=True)
            image = await self._get_image(obraz) if obraz else None
            if not (tresc or image):
                await interaction.followup.send(embed=get_status_embed("Czego szukamy?", HELP_TEXT))
                return
            for embeds in await self._get_reply(interaction.user.id, tresc or "", image):
                await interaction.followup.send(embeds=embeds)

        @self.tree.command(name="usun_moje_dane", description="Usuń swoje sprawdzenia z serwera Prawdowida")
        @app_commands.allowed_installs(guilds=True, users=True)
        @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
        async def delete_command(interaction: discord.Interaction) -> None:
            await interaction.response.defer(ephemeral=True, thinking=True)
            try:
                await self.api.delete_session(interaction.user.id)
                text = "Usunęliśmy Twoje sprawdzenia z serwera Prawdowida."
            except ApiUnavailableError:
                text = "Nie udało się teraz usunąć danych. Spróbuj ponownie za chwilę."
            await interaction.followup.send(text, ephemeral=True)

        @self.tree.context_menu(name="Sprawdź w Prawdowid")
        @app_commands.allowed_installs(guilds=True, users=True)
        @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
        async def check_message(interaction: discord.Interaction, message: discord.Message) -> None:
            """Right-click any message → Apps → Sprawdź w Prawdowid. The reply is visible only to the
            person who asked, so it works in any server or DM without adding the bot there."""
            await interaction.response.defer(ephemeral=True, thinking=True)
            image_attachment = next(
                (a for a in message.attachments if (a.content_type or "").startswith("image/")), None
            )
            image = await self._get_image(image_attachment) if image_attachment else None
            if not (message.content.strip() or image):
                await interaction.followup.send(
                    embed=get_status_embed("Brak treści", "Ta wiadomość nie zawiera tekstu ani obrazu do sprawdzenia."),
                    ephemeral=True,
                )
                return
            for embeds in await self._get_reply(interaction.user.id, message.content, image):
                await interaction.followup.send(embeds=embeds, ephemeral=True)

    async def setup_hook(self) -> None:
        guild_id = self.settings.discord_guild_id
        if guild_id:
            guild = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        await self.tree.sync()  # global: needed for user installs (can take a while to appear)

    async def on_ready(self) -> None:
        logger.info("Prawdowid bot ready as %s", self.user)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or self.user is None:
            return
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mention = self.user in message.mentions
        if not (is_dm or is_mention):
            return
        text = re.sub(rf"<@!?{self.user.id}>", "", message.content).strip()
        image_attachment = next((a for a in message.attachments if (a.content_type or "").startswith("image/")), None)
        image = await self._get_image(image_attachment) if image_attachment else None
        if not (text or image):
            await message.reply(embed=get_status_embed("Jak mogę pomóc?", HELP_TEXT), mention_author=False)
            return
        async with message.channel.typing():
            replies = await self._get_reply(message.author.id, text, image)
        for embeds in replies:
            await message.reply(embeds=embeds, mention_author=False)

    async def _get_image(self, attachment: discord.Attachment) -> bytes | None:
        if attachment.size > MAX_IMAGE_BYTES or not (attachment.content_type or "").startswith("image/"):
            return None
        return await attachment.read()

    async def _get_reply(self, user_id: int, text: str, image: bytes | None) -> list[list[discord.Embed]]:
        try:
            result = await self.api.check(user_id, get_check_input(text, image))
        except ApiUnavailableError as error:
            logger.warning("API unavailable: %s", error)
            return [[get_unavailable_embed()]]
        return get_result_embeds(result, self.settings.web_base_url)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    bot = PrawdowidBot()
    bot.run(bot.settings.discord_token.get_secret_value(), log_handler=None)
