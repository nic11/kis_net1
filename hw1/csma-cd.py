#!/usr/bin/env python3
#coding: utf-8

import random


class Frame:
    SIZE_LIMIT = 4

    def __init__(self, data: bytes, peer_id=None):
        if data is not None and len(data) > Frame.SIZE_LIMIT:
            raise Exception('frame too big')
        self._data = data
        self._peer_id = peer_id
    
    def is_corrupt(self):
        return self._data is None

    def is_silence(self):
        return self._data == b''
    
    def get_data(self):
        assert not self.is_corrupt()
        return self._data

    def get_peer_id(self):
        return self._peer_id

    def __repr__(self):
        if self.is_corrupt():
            return 'Frame.CORRUPT'
        if self.is_silence():
            return 'Frame.SILENCE'
        return 'Frame(data=' + repr(self._data) + ', peer_id=' + str(self._peer_id) + ')'

    @classmethod
    def split_data_into_frames(cls, data, peer_id):
        frame_cnt = (len(data) + Frame.SIZE_LIMIT - 1) // Frame.SIZE_LIMIT

        frames = []
        start = 0
        while start < len(data):
            frames.append(Frame(data[start:start + Frame.SIZE_LIMIT], peer_id))
            start += Frame.SIZE_LIMIT
        
        assert len(frames) == frame_cnt
        assert sum(map(lambda frame: len(frame.get_data()), frames)) == len(data)
    
        return frames


Frame.SILENCE = Frame(b'')
Frame.CORRUPT = Frame(None)


class Channel:
    def __init__(self):
        self.tick = 0
        self.peers = []
    
    def register_peer(self, peer):
        self.peers.append(peer)
    
    def do_tick(self):
        tick = self.tick
        self.tick += 1
        
        print('Tick:', tick)

        tried_frames = []
        for peer in self.peers:
            frame = peer.before_tick(tick)
            print('Peer', peer.peer_id, 'tried to send', repr(frame))
            if not frame.is_silence():
                tried_frames.append(frame)

        print('Tried to send', ', '.join(map(lambda p: str(p.peer_id), self.peers)))
        
        frame = None
        if len(tried_frames) == 0:
            frame = Frame.SILENCE
        elif len(tried_frames) == 1:
            frame = tried_frames[0]
        else:
            frame = Frame.CORRUPT

        print('Won frame by', frame._peer_id)
        
        for peer in self.peers:
            peer.after_tick(tick, frame)

        return frame
    
    def all_done(self):
        for peer in self.peers:
            if not peer.is_done():
                return False
        return True


class Peer:
    def __init__(self, data, peer_id):
        # Data we want to transmit
        self.frames = Frame.split_data_into_frames(data, peer_id)
        
        # State
        self.is_transmitting = False
        self.transmitted_frames = 0
        self.sleep_for = 0
        self.somebody_was_transmitting = False

        # Used to build timeline
        self.peer_id = peer_id

        print('Peer', peer_id)
        for frame in self.frames:
            print(' data=', repr(frame.get_data()))

    def before_tick(self, tick):
        if self.transmitted_frames != len(self.frames) and self.sleep_for == 0 \
                and not self.somebody_was_transmitting:
            self.is_transmitting = True

        if self.is_transmitting:
            return self.frames[self.transmitted_frames]
        return Frame.SILENCE  # might be either sleeping or not having data to send

    def after_tick(self, tick, frame):
        somebody_was_transmitting_before = self.somebody_was_transmitting
        self.somebody_was_transmitting = \
            not frame.is_silence() and frame.get_peer_id() != self.peer_id

        if frame.is_corrupt():
            self.sleep_for = random.randint(0, 15)  # up to 16 ticks
            self.is_transmitting = False
            return

        if self.sleep_for > 0:
            assert not self.is_transmitting
            self.sleep_for -= 1
            return
        
        if self.is_transmitting:
            assert frame is self.frames[self.transmitted_frames]
            self.transmitted_frames += 1
            if self.transmitted_frames == len(self.frames):
                self.is_transmitting = False
            return

        if not somebody_was_transmitting_before:
            # else, we had C H I L L
            assert not self.is_transmitting
            assert self.sleep_for == 0
            assert self.transmitted_frames == len(self.frames)
    
    def is_done(self):
        return self.transmitted_frames == len(self.frames)


random.seed(1337)

channel = Channel()

channel.register_peer(Peer(b'Some data by peer 0', 0))
channel.register_peer(Peer(b"Hello, I'm 1", 1))
channel.register_peer(Peer(b"Dancin' is what to do", 2))

frames = []

while not channel.all_done():
    frames.append(channel.do_tick())

print()
print('Final state:')
for i, frame in enumerate(frames):
    # print(i, 'frame=' + repr(frame._data), 'peer_id=' + str(frame._peer_id), sep='\t')
    print(i, frame)

