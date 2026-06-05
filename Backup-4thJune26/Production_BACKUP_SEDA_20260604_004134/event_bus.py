import queue

# Global Event Queues for IPC
signal_queue = queue.Queue()
exit_queue = queue.Queue()
dashboard_queue = queue.Queue()
log_queue = queue.Queue()
manual_exits = set()
