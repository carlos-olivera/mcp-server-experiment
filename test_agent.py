import asyncio
from twitter_agent import TwitterAgent

async def main():
    agent = TwitterAgent()
    await agent.start()
    print("Ventana abierta con la sesión de X. Esperando 10 segundos...")
    await asyncio.sleep(10)
    await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())