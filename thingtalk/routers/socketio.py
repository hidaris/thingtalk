from .socket_manager import SocketManager

from ..app import app


sio = SocketManager(app=app)


@app.sio.on('join')
async def handle_join(sid, *args, **kwargs):
    await sio.emit('lobby', 'User joined')


@sio.on('test')
async def test(sid, *args, **kwargs):
    await sio.emit('hey', 'joe')
