import asyncio
import random
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlencode
import ssl
from aiolimiter import AsyncLimiter
import config_file

rate_limit = 18  # Maximum X concurrent requests at a time

# Configure SSL context to ignore certificate verification (use with caution)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


async def check_indexed(session, url, limiter):
    ua = random.choice(config_file.user_agents_list)
    headers = {
        'User-Agent': ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0"
    }

    query = {'q': 'site:' + url}
    google = "https://www.google.com/search?" + urlencode(query)

    async with limiter:
        while True:
            try:
                async with session.get(google, headers=headers, proxy=config_file.proxy, ssl=ssl_context) as resp:
                    data = await resp.text()
                    soup = BeautifulSoup(data, "html.parser")

                    try:
                        check = soup.find_all('div', class_=lambda x: x and 'kCrYT' in x.split())[0].find("h3")
                        if check:
                            return (url, "True")
                        else:
                            return (url, "False")
                    except TypeError:
                        return (url, "False")
                    except IndexError:
                        raise
            except ssl.SSLError as e:
                print(f"SSL error for URL {url}: {e}. Retrying...")
                await asyncio.sleep(5)
            except aiohttp.ClientResponseError as e:
                if e.status == 429:
                    print(f"Too Many Requests (429) for URL {url}. Retrying...")
                    await asyncio.sleep(10)
                else:
                    print(e)
                    return (url, "RequestError")
            except aiohttp.ClientError as e:
                print(f"Request failed: {e}")
                return (url, "RequestError")
            except Exception as e:
                print(f"Unexpected error for URL {url}: {e}")
                return (url, "Error")


async def main(urls, timeout=180):
    async with aiohttp.ClientSession() as session:
        limiter = AsyncLimiter(rate_limit, 1)
        tasks = [asyncio.create_task(check_indexed(session, url.strip(), limiter)) for url in urls]
        try:
            results = await asyncio.wait_for(asyncio.gather(*tasks), timeout)
            return results
        except asyncio.TimeoutError:
            print(f"Task timed out after {timeout} seconds")
            # Cancel pending tasks
            for task in tasks:
                task.cancel()
            # Ensure all tasks are cleaned up
            await asyncio.gather(*tasks, return_exceptions=True)
            # Return whatever results were completed within the timeout
            results = [task.result() if task.done() else (urls[i], "Timeout") for i, task in enumerate(tasks)]
            return results