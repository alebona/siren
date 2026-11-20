# -*- coding: utf-8 -*-
"""
Async counterpart of core._wrap, for coroutine functions (async def views in
FastAPI, Starlette, Django, Quart...). Kept in its own module because the
async syntax doesn't parse on Python 2; it's only imported on Python 3.
"""
import functools


def wrap_async(target, before, after, on_error):
    @functools.wraps(target)
    async def wrapper(*args, **kwargs):
        state = before(args, kwargs)
        try:
            result = await target(*args, **kwargs)
        except Exception as e:
            on_error(e, state)
            raise
        after(result, state)
        return result

    return wrapper
