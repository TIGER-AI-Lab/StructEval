import argparse
import asyncio
import json
import os

import toml
from aioconsole import ainput, aprint
from bs4 import BeautifulSoup
import playwright.async_api
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from tqdm.asyncio import tqdm

from utils.axtree import TextObervationProcessor
from utils.browser_helper import (get_interactive_elements_with_playwright,
                                  normal_launch_async,
                                  normal_new_context_async)


def get_meta_info(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    try:
        description_meta = soup.find('meta', attrs={'name': 'description'})
        description_content = description_meta['content']
    except:
        description_content = None

    soup = BeautifulSoup(html_content, 'html.parser')
    try:
        description_meta_property = soup.find('meta', attrs={'property': 'og:description'})
        description_content_property = description_meta_property['content']
    except:
        description_content_property = None
    
    try:
        title_meta = soup.find('meta', attrs={'name': 'title'})
        title_content = title_meta['content']
    except:
        title_content = None

    try:
        title2_meta = soup.find('title')
        title2_content = title2_meta.get_text()
    except:
        title2_content = None
    return title_content, title2_content, description_content, description_content_property


async def scroll(page):
    # This method mimics the JS code you provided.
    await page.evaluate("""
        (async () => {
            return new Promise((resolve, reject) => {
                var i = setInterval(() => {
                    window.scrollBy(0, window.innerHeight);
                    if (
                        document.scrollingElement.scrollTop + window.innerHeight >=
                        document.scrollingElement.scrollHeight
                    ) {
                        window.scrollTo(0, 0);
                        clearInterval(i);
                        resolve();
                    }
                }, 100);
            });
        })();
    """)


async def get_webpage_info(
    args,
    current_page, 
    url, 
    output_path, 
    viewport_size,
):
    # open the website
    try:
        await current_page.goto(url, wait_until="load", timeout=args.open_timeout * 1000)
    except Exception as e:
        await aprint("Failed to fully load the webpage before timeout")
        await aprint(e)
        return [], None

    try:
        await current_page.wait_for_load_state("domcontentloaded", timeout=3000)
    except playwright.async_api.Error:
        pass
    for frame in current_page.frames:
        try:
            await frame.wait_for_load_state("domcontentloaded", timeout=3000)
        except playwright.async_api.Error:
            pass

    # await asyncio.sleep(3)
    
    # get title content
    try:
        root_html_content = await current_page.content()
    except Exception as e:
        # Exception: Unable to retrieve content because the page is navigating and changing the content.
        await aprint(f"exception during current_page.content(): {str(e)}")
        return [], None
    
    title_content, title2_content, description_content1, description_content2 = get_meta_info(root_html_content)

    meta_info = description_content1 or description_content2
    json.dump(
        {"url": url, "meta": meta_info},
        open(os.path.join(output_path, f'meta_info.json'), 'w'),
        indent=2,
    )

    # some website will lazy load images
    # https://screenshotone.com/blog/a-complete-guide-on-how-to-take-full-page-screenshots-with-puppeteer-playwright-or-selenium/#animations-are-played-only-on-the-page-scroll
    await scroll(current_page)

    # save screenshots
    cur_screenshot = f'0.{args.image_format}'
    input_image_path = os.path.join(output_path, cur_screenshot)
    try:
        if args.image_format == 'jpg':
            await current_page.screenshot(
                path=input_image_path,
                full_page=args.full_page_screenshot,
                type='jpeg',
                quality=100,
                timeout=args.screenshot_timeout*1000
            )
        else:
            assert args.image_format == 'png'
            await current_page.screenshot(
                path=input_image_path,
                full_page=args.full_page_screenshot,
                type='png',
                timeout=args.screenshot_timeout*1000
            )
    except Exception as e_clip:
        await aprint(f"Failed to get cropped screenshot because {e_clip}")
        return [], None

    axtree_processor = TextObervationProcessor(
        'accessibility_tree', current_viewport_only=False, viewport_size=viewport_size
    )
    cdp_client = await current_page.context.new_cdp_session(current_page)
    axtree_step1_raw_node_list, axtree_step2_parsed_content, axtree_step2_parsed_nodeinfo, axtree_step3_cleaned_content = await axtree_processor.process(current_page, cdp_client, None, None)

    json.dump(axtree_step2_parsed_nodeinfo, open(os.path.join(output_path, f'axtree_nodeinfo.json'), 'w'), indent=2)
    with open(os.path.join(output_path, f'axtree_content.txt'), 'w') as fw:
        fw.write(axtree_step3_cleaned_content)

    await cdp_client.detach()


async def get_webpage_shot(args, config, start_url, confirmed_website):
    # playwright settings
    save_video = config["playwright"]["save_video"]
    tracing = config["playwright"]["tracing"]
    locale = config["playwright"].get("locale", None)
    geolocation = config["playwright"].get("geolocation", None)
    trace_screenshots = config["playwright"]["trace"]["screenshots"]
    trace_snapshots = config["playwright"]["trace"]["snapshots"]
    trace_sources = config["playwright"]["trace"]["sources"]
    storage_state = config["basic"].get("storage_state", None)
    viewport_size = config["playwright"]["viewport"]

    task_id = confirmed_website
    output_path = os.path.join(args.output_path, task_id)

    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    async with async_playwright() as playwright:
        browser = await normal_launch_async(
            playwright,
            headless=True,
            proxy={'server': proxy_address} if proxy_address is not None else None
        )

        if args.device_type == 'pc':
            config_kwargs = {
                'user_agent': "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
                'viewport': {'width': viewport_size['width'], 'height': viewport_size['height']},
                'device_scale_factor': 1.0
            }
        elif args.device_type == 'iPhone 12 Pro':
            config_kwargs = {
                'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
                'viewport': {'width': viewport_size['width'], 'height': viewport_size['height']},
                'device_scale_factor': 3,
                'is_mobile': True,
                'has_touch': True,
                'default_browser_type': 'webkit'
            }
        else:
            assert False

        context = await normal_new_context_async(
            browser,
            tracing=tracing,
            storage_state=storage_state,
            video_path=output_path if save_video else None,
            trace_screenshots=trace_screenshots,
            trace_snapshots=trace_snapshots,
            trace_sources=trace_sources,
            geolocation=geolocation,
            locale=locale,
            **config_kwargs,
        )
        
        current_page = await context.new_page()
        await stealth_async(current_page)
        
        await get_webpage_info(
            args,
            current_page, 
            start_url,
            output_path, 
            viewport_size,
        )

        close_context = context
        await close_context.close()


async def main(args, config, website_dict) -> None:
    website_dict_keys = sorted(list(website_dict.keys()))

    tasks = [get_webpage_shot(args, config, website_dict[confirmed_website], confirmed_website) for confirmed_website in website_dict_keys]

    for i in range(0, len(tasks), args.batch_size):
        for task in tqdm(asyncio.as_completed(tasks[i:i+args.batch_size]), total=len(tasks[i:i+args.batch_size])):
            await task


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--config_path", type=str, metavar='config', default=f"{os.path.join('config', 'demo_mode.toml')}")
    parser.add_argument('--device_type', type=str, default='pc')
    parser.add_argument('--image_format', type=str, default='png')
    parser.add_argument('--open_timeout', type=int, default=30) # seconds
    parser.add_argument('--screenshot_timeout', type=int, default=10)   # seconds
    parser.add_argument('--batch_size', type=int, default=20)
    parser.add_argument('--full_page_screenshot', default=True, type=str2bool)
    parser.add_argument('--output_path', type=str, default='webpage_shots')
    args = parser.parse_args()

    proxy_address = os.environ.get('https_proxy', None)
    
    config = toml.load(open(args.config_path, 'r'))

    # website_dict = json.load(open("data/GUIbench_websites_dict_filtered.json"))
    website_dict = {"animals": "https://a-z-animals.com/"}
    
    asyncio.run(main(args, config, website_dict))
