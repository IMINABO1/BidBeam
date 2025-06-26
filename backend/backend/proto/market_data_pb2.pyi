from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Order(_message.Message):
    __slots__ = ("order_id", "price", "quantity", "side", "order_type", "timestamp")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    ORDER_TYPE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    order_id: int
    price: float
    quantity: int
    side: bool
    order_type: str
    timestamp: float
    def __init__(self, order_id: _Optional[int] = ..., price: _Optional[float] = ..., quantity: _Optional[int] = ..., side: bool = ..., order_type: _Optional[str] = ..., timestamp: _Optional[float] = ...) -> None: ...

class Trade(_message.Message):
    __slots__ = ("buy_order_id", "sell_order_id", "price", "quantity", "timestamp")
    BUY_ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    SELL_ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    buy_order_id: int
    sell_order_id: int
    price: float
    quantity: int
    timestamp: float
    def __init__(self, buy_order_id: _Optional[int] = ..., sell_order_id: _Optional[int] = ..., price: _Optional[float] = ..., quantity: _Optional[int] = ..., timestamp: _Optional[float] = ...) -> None: ...

class OrderBookLevel(_message.Message):
    __slots__ = ("price", "quantity")
    PRICE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    price: float
    quantity: int
    def __init__(self, price: _Optional[float] = ..., quantity: _Optional[int] = ...) -> None: ...

class OrderBookSnapshot(_message.Message):
    __slots__ = ("instrument_id", "bids", "asks", "timestamp")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    BIDS_FIELD_NUMBER: _ClassVar[int]
    ASKS_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    bids: _containers.RepeatedCompositeFieldContainer[OrderBookLevel]
    asks: _containers.RepeatedCompositeFieldContainer[OrderBookLevel]
    timestamp: float
    def __init__(self, instrument_id: _Optional[str] = ..., bids: _Optional[_Iterable[_Union[OrderBookLevel, _Mapping]]] = ..., asks: _Optional[_Iterable[_Union[OrderBookLevel, _Mapping]]] = ..., timestamp: _Optional[float] = ...) -> None: ...

class OrderBookUpdate(_message.Message):
    __slots__ = ("instrument_id", "price", "quantity", "side", "timestamp")
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    price: float
    quantity: int
    side: bool
    timestamp: float
    def __init__(self, instrument_id: _Optional[str] = ..., price: _Optional[float] = ..., quantity: _Optional[int] = ..., side: bool = ..., timestamp: _Optional[float] = ...) -> None: ...

class SubscriptionRequest(_message.Message):
    __slots__ = ("instrument_id",)
    INSTRUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    instrument_id: str
    def __init__(self, instrument_id: _Optional[str] = ...) -> None: ...

class MarketDataResponse(_message.Message):
    __slots__ = ("snapshot", "update")
    SNAPSHOT_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FIELD_NUMBER: _ClassVar[int]
    snapshot: OrderBookSnapshot
    update: OrderBookUpdate
    def __init__(self, snapshot: _Optional[_Union[OrderBookSnapshot, _Mapping]] = ..., update: _Optional[_Union[OrderBookUpdate, _Mapping]] = ...) -> None: ...
