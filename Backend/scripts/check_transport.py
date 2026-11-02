import asyncio
import json
import sys

from app.providers.registry import get_transport


async def main() -> None:
    origin, destination = sys.argv[1], sys.argv[2]
    day = sys.argv[3] if len(sys.argv) > 3 else ""
    provider = get_transport()
    print("provider:", provider.name)
    result = await provider.search(origin, destination, day)
    print("note:", result["note"])
    print("options:", len(result["options"]))
    print(json.dumps(result["options"], ensure_ascii=False, indent=2))


asyncio.run(main())
