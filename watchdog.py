


#   To get failures / crashes, we will monitor the VM state, container state, and VM logs from the cron job
#   Optionally, we can have another container stream logs from a logs volume on the VM to get live PUBLIC logs
import random
import string
import time


def run():
    start = time.time()
    cron_run_id = ''.join(random.choice(string.ascii_uppercase + string.digits)
                          for _ in range(6))
    index = 0
    while time.time() - start < 59:
        index += 1
        print(cron_run_id, time.time(), index)
        time.sleep(1)

    print('ending ' + cron_run_id)


if __name__ == '__main__':
    run()
