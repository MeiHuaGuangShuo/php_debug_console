<?php

class Logger {
    private string $url;
    private string $log_file;
    private array $log_levels = ['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL'];
    public int $log_level_limit = 2;
    private array $log_handlers = [];
    public bool $log_to_file_as_json = false;
    private int $stop_http_requests = 0;

    public function __construct(string $url, string $log_file = "") {
        $this->url = $url;
        $this->log_file = $log_file;
    }

    public function add_handler(callable $handler) {
        if (!is_callable($handler)) {
            throw new InvalidArgumentException('Handler must be a callable array.');
        }
        try {
            $reflection = new ReflectionFunction($handler);
            $parameters = $reflection->getParameters();
            if (count($parameters) !== 1) {
                throw new InvalidArgumentException('Handler must accept exactly one parameter.');
            }
            $this->log_handlers[] = $handler;
        } catch (ReflectionException $e) {
            throw new InvalidArgumentException('Handler must be a callable.');
        }
    }


    public function change_level(string $level): bool
    {
        $level_no = array_search(strtoupper($level), $this->log_levels);
        if (!(is_int($level_no) && $level_no >= 0 && $level_no <= 6)) {
            return false;
        }
        $this->log_level_limit = $level_no;
        return true;
    }

    private function _send_log($level, $message) {
        $level_no = array_search(strtoupper($level), $this->log_levels);
        if (!$level_no >= $this->log_level_limit) {
            return;
        }
        $trace = debug_backtrace(DEBUG_BACKTRACE_IGNORE_ARGS, 2)[1];
        $file_name = $trace['file'];
        $line_no = $trace['line'];
        $timestamp = date('Y-m-d H:i:s') . '.' . substr(microtime(), 2, 3);
        if (!is_string($message)) {
            $message = json_encode($message, JSON_UNESCAPED_UNICODE);
        }
        $log_data = [
            "file" => $file_name,
            "function" => debug_backtrace(DEBUG_BACKTRACE_IGNORE_ARGS, 3)[2]['function'],  // Unsolved problem: The second function name is not correct
            "line_no" => $line_no,
            "message" => base64_encode($message),
            "level" => $level,
            "timestamp" => $timestamp
        ];
        if ($this->log_handlers) {
            foreach ($this->log_handlers as $handler) {
                $handler($log_data);
            }
        }
        if ($this->log_file) {
            if (!file_exists($this->log_file)) {
                fclose(fopen($this->log_file, "w"));
            }
            if (!$this->log_to_file_as_json){
                $data = $timestamp . " | " . str_pad($level, 8) . " | " . $log_data['file'] . ":" . $log_data['function'] . ":" . $log_data['line_no'] . " - " . $message . "\n";
            } else {
                $data = json_decode(json_encode($log_data), true);
                $data["message"] = $message;
                $data = json_encode($data)."\n";
            }
            file_put_contents($this->log_file, $data, FILE_APPEND);
        }

        try {
            if (time() > $this->stop_http_requests && $this->url) {
                $ch = curl_init($this->url);
                curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
                curl_setopt($ch, CURLOPT_HTTPHEADER, ["Content-type: application/json"]);
                curl_setopt($ch, CURLOPT_POST, true);
                curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($log_data));
                curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 1);
                curl_setopt($ch, CURLOPT_TIMEOUT, 1);

                $response = curl_exec($ch);
                if ($response === false) {
                    $this->stop_http_requests = time() + 60;
                    $this->_send_log('ERROR', 'Failed to send log to server. Reason: '. curl_error($ch));
                }
                curl_close($ch);
            }
        } catch (Exception $e) {
            $this->stop_http_requests = time() + 60;
            $this->_send_log('ERROR', 'Failed to send log to server. Reason: '. $e->getMessage());
        }

    }

    public function trace($message) {
        $this->_send_log('TRACE', $message);
    }

    public function debug($message) {
        $this->_send_log('DEBUG', $message);
    }

    public function info($message) {
        $this->_send_log('INFO', $message);
    }

    public function warning($message) {
        $this->_send_log('WARNING', $message);
    }

    public function success($message) {
        $this->_send_log('SUCCESS', $message);
    }

    public function error($message) {
        $this->_send_log('ERROR', $message);
    }

    public function critical($message) {
        $this->_send_log('CRITICAL', $message);
    }
}

function test_handler(array $log_data)
{
    printf("%s | %s | %s:%s:%s - %s\n", $log_data['timestamp'], str_pad($log_data['level'], 8), $log_data['file'],$log_data['function'],$log_data['line_no'],base64_decode($log_data['message']));
}

function main()
{
    // 示例用法
    $logger = new Logger('http://localhost:60721/log', "log.txt");
    $logger->add_handler('test_handler');
    $logger->trace('This is log message');
    $logger->debug('This is a debug message');
    $logger->info('This is an info message');
    $logger->warning('This is a warning message');
    $logger->success('This is a success message');
    $logger->error('This is an error message');
    $logger->critical('This is a critical message');
    // 示例用法2 纯本地日志
    $logger = new Logger('', "log.txt");
    $logger->log_to_file_as_json = true;
    $logger->add_handler('test_handler');
    $logger->trace('This is log message');
    $logger->debug('This is a debug message');
    $logger->info('This is an info message');
    $logger->warning('This is a warning message');
    $logger->success('This is a success message');
    $logger->error('This is an error message');
    $logger->critical('This is a critical message');
}

main();
