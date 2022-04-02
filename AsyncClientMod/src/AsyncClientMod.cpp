#include "AsyncClientMod.h"

__attribute__((unused)) size_t AsyncClientMod::write_all(const char * data) {
    if (data == nullptr) {
        return 0;
    }

    return write_all(data, strlen(data));
}

size_t AsyncClientMod::write_all(const char * data, size_t size) {
    if (data == nullptr || size == 0) {
        return 0;
    }

    assert(_datasource == nullptr);
    assert(!_send_waiting);

    _datasource = data;
    _datalen = size;
    _written = 0;

    do {
        if (_write_some()) {
            _write_start_time = millis();
        }

        if (_written == _datalen || _is_timeout() || _is_closed()) {
            _datasource = nullptr;
            _datalen = 0;
            break;
        }

        _send_waiting = true;
        esp_delay(_ack_timeout, [this]() { return this->_send_waiting; }, 1);
        _send_waiting = false;
    } while (true);

    return _written;
}

bool AsyncClientMod::_write_some() {
    if (!_pcb || !_datasource) {
        return false;
    }

    bool has_written = false;
    while (_written < _datalen) {
        if (_is_closed())
            return false;

        const auto remaining = _datalen - _written;
        size_t next_chunk_size = std::min((size_t) tcp_sndbuf(_pcb), remaining);
        if (!next_chunk_size)
            break;

        const char * buf = _datasource + _written;
        uint8_t flags = 0;
        if (next_chunk_size < remaining) {
            flags |= TCP_WRITE_FLAG_MORE;
        }

        esp_err_t err = _tcp_write(_pcb, _closed_slot, buf, next_chunk_size, flags);
        if (err != ERR_OK) {
            break;
        }

        _written += next_chunk_size;
        has_written = true;
    }

    if (!has_written) {
        return false;
    }

    return send();
}

bool AsyncClientMod::_is_timeout() {
    return millis() - _write_start_time > _ack_timeout;
}

bool AsyncClientMod::_is_closed() {
    if (!_pcb) {
        return true;
    }

    uint8_t st = state();
    return st == CLOSED || st == CLOSE_WAIT || st == CLOSING;
}