#pragma once

#include <iostream>
#include <string>
#include <ctime>
#include <map>
#include <algorithm> 
#include <functional>
#include <utility>
#include <stdexcept>
#include <unordered_map>
#include <memory>
#include <optional>
#include <vector>
#include <queue>
#include <chrono>
#include <thread>

#include <librdkafka/rdkafka.h>
#include <nlohmann/json.hpp>

// Forward declarations
class Order;
class Trade;

enum class OrderType {
    LIMIT,
    MARKET
};

class Trade {
public:
    int buy_order_id;
    int sell_order_id;
    double price;
    unsigned int quantity;
    std::chrono::time_point<std::chrono::steady_clock> timestamp;

    Trade(int buy_id, int sell_id, double p, unsigned int qty);
    void repr() const;
};

class Order {
public:
    Order(int id, double p, unsigned int qty, bool s, std::time_t t,
          OrderType type = OrderType::LIMIT,
          std::optional<std::chrono::seconds> ttl = std::nullopt);
    void repr() const;
    bool operator==(const Order& other) const;

    int get_order_id() const;
    double get_price() const;
    unsigned int get_qty() const;
    bool get_side() const;
    time_t get_timestamp() const;
    OrderType get_order_type() const;
    std::chrono::time_point<std::chrono::steady_clock> get_creation_time() const;
    bool is_expired() const;
    void set_price(double new_price);
    void set_qty(unsigned int new_qty);
    void set_side(bool new_side);
    void toggle_side();
    ~Order();

private:
    int _order_id;
    double _price;
    unsigned int _quantity;
    bool _side; // True for Buy, False for Sell
    std::time_t _timestamp;
    OrderType _order_type;
    std::optional<std::chrono::time_point<std::chrono::steady_clock>> _expiry_time;
    std::chrono::time_point<std::chrono::steady_clock> _creation_time;
};

struct BuyOrderComparator {
    bool operator()(const std::pair<Order, std::chrono::time_point<std::chrono::steady_clock>>& a,
                    const std::pair<Order, std::chrono::time_point<std::chrono::steady_clock>>& b) const;
};

struct SellOrderComparator {
    bool operator()(const std::pair<Order, std::chrono::time_point<std::chrono::steady_clock>>& a,
                    const std::pair<Order, std::chrono::time_point<std::chrono::steady_clock>>& b) const;
};

// Delivery report callback for librdkafka
void dr_msg_cb(rd_kafka_t *rk, const rd_kafka_message_t *rkmessage, void *opaque);

class OrderBook {
public:
    OrderBook();
    ~OrderBook();

    std::vector<Trade> add_order(const Order& order);
    void add_order_legacy(const Order& order);
    void remove_order(const int order_id);
    void clean_expired_orders();
    void repr();
    void repr(bool side);
    Order get_best_bid() const;
    Order get_best_ask() const;
    void update_order(int order_id, std::optional<double> new_price,
                      std::optional<unsigned int> new_qty, std::optional<bool> new_side);
    const std::vector<Trade>& get_trade_log() const;
    void repr_trade_log() const;

private:
    std::priority_queue<std::pair<Order, std::chrono::time_point<std::chrono::steady_clock>>,
                        std::vector<std::pair<Order, std::chrono::time_point<std::chrono::steady_clock>>>
                        , BuyOrderComparator> _buy_orders;

    std::priority_queue<std::pair<Order, std::chrono::time_point<std::chrono::steady_clock>>,
                        std::vector<std::pair<Order, std::chrono::time_point<std::chrono::steady_clock>>>
                        , SellOrderComparator> _sell_orders;

    std::unordered_map<int, std::shared_ptr<Order>> _order_lookup;
    std::vector<Trade> _trade_log;
    rd_kafka_t *_producer;
    rd_kafka_conf_t *_conf;

    std::vector<Trade> match_order(const Order& incoming_order);
    void add_order_to_book(const Order& order);
    void flip_order(int order_id);
};