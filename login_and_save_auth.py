
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# PERFIL REAL DE CHROMIUM SNAP
USER_DATA_DIR = "/home/parallels/snap/chromium/common/chromium"
CHROMIUM_EXECUTABLE = "/snap/bin/chromium"

TWITTER_URL = "https://x.com/home"

async def main():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            executable_path=CHROMIUM_EXECUTABLE,
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = context.pages[0] if context.pages else await context.new_page()

        print(">>> Abriendo X...")
        try:
            # ¡IMPORTANTE! No usamos networkidle porque X nunca se queda “quieto”
            await page.goto(TWITTER_URL, wait_until="domcontentloaded", timeout=60000)
        except PlaywrightTimeoutError:
            print(">>> Aviso: timeout cargando X, pero continuamos igual...")

        print("\n>>> Deberías ver la MISMA sesión que en Chromium normal.")
        print(">>> Si no estás logueado, inicia sesión aquí mismo (es el mismo perfil).")
        input(">>> Cuando veas tu timeline / home, pulsa ENTER aquí en la terminal...\n")

        await context.storage_state(path="auth.json")
        print(">>> auth.json generado correctamente en el directorio actual.")

        await context.close()

if __name__ == "__main__":
    asyncio.run(main())