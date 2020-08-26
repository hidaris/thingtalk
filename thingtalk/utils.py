"""Utility functions."""

import datetime
import ifaddr
import socket
import asyncio

from contextlib import contextmanager
from threading import Thread


def get_ws_href(request):
    scheme = 'wss' if request.url.scheme == 'https' else 'ws'
    host = request.headers.get('Host', '')
    href = f"{scheme}://{host}"
    return href


def get_http_href(request):
    scheme = request.url.scheme
    host = request.headers.get('Host', '')
    href = f"{scheme}://{host}"
    return href


def timestamp():
    """
    Get the current time.
    Returns the current time in the form YYYY-mm-ddTHH:MM:SS+00:00
    """
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00")


def get_ip():
    """
    Get the default local IP address.
    From: https://stackoverflow.com/a/28950776
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except (socket.error, IndexError):
        ip = "127.0.0.1"
    finally:
        s.close()

    return ip


def get_addresses():
    """
    Get all IP addresses.
    Returns list of addresses.
    """
    addresses = set()

    for iface in ifaddr.get_adapters():
        for addr in iface.ips:
            # Filter out link-local addresses.
            if addr.is_IPv4:
                ip = addr.ip

                if not ip.startswith("169.254."):
                    addresses.add(ip)
            elif addr.is_IPv6:
                # Sometimes, IPv6 addresses will have the interface name
                # appended, e.g. %eth0. Handle that.
                ip = addr.ip[0].split("%")[0].lower()

                if not ip.startswith("fe80:"):
                    addresses.add(f"[{ip}]")

    return sorted(list(addresses))


@contextmanager
def background_thread_loop():
    def run_forever(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    loop = asyncio.new_event_loop()
    try:
        thread = Thread(target=run_forever, args=(loop,))
        thread.start()
        yield loop
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join()
