#!/usr/bin/env python3

import argparse
import sys
import time
# import RPi.GPIO as GPIO  # Not needed for I2C relay hat
import SM16relind


def test_relay_hat():
    try:
        # Initialize the relay hat (using index 0 for the first hat)
        print("Initializing relay hat...")
        relay_hat = SM16relind.SM16relind(0)

        # Test 1: Individual relay test
        print("\nTest 1: Testing each relay individually...")
        for relay in range(1, 17):
            print(f"Activating relay {relay}")
            relay_hat.set(relay, 1)  # Turn on
            time.sleep(1)
            relay_hat.set(relay, 0)  # Turn off
            time.sleep(0.5)

        # Test 2: All relays on/off
        print("\nTest 2: Testing all relays together...")
        print("Turning all relays ON")
        relay_hat.set_all(1)
        time.sleep(2)
        print("Turning all relays OFF")
        relay_hat.set_all(0)
        time.sleep(1)

        # Test 3: Sequential pattern
        print("\nTest 3: Running sequential pattern...")
        for _ in range(2):  # Run pattern twice
            # Turn on relays in sequence
            for relay in range(1, 17):
                relay_hat.set(relay, 1)
                time.sleep(0.2)
            # Turn off relays in sequence
            for relay in range(1, 17):
                relay_hat.set(relay, 0)
                time.sleep(0.2)

        print("\nRelay hat testing completed successfully!")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        # Ensure all relays are turned off
        try:
            if 'relay_hat' in locals():
                relay_hat.set_all(0)
        except Exception:
            pass
        # NOTE: SM16relind uses I2C, so RPi.GPIO.cleanup() is not needed 
        # and causes RuntimeWarning if no GPIOs were used.


def cli_control():
    parser = argparse.ArgumentParser(
        description="CLI to control individual relays on the Sequent 16-Relays HAT (stack=0 default)."
    )
    parser.add_argument(
        "--relay",
        "-r",
        type=int,
        nargs="+",
        choices=range(1, 17),
        required=True,
        help="One or more relay channels to control (1-16).",
    )
    parser.add_argument(
        "--stack",
        "-s",
        type=int,
        default=0,
        choices=range(0, 8),
        help="HAT stack level (0-7). Default: 0",
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--on", action="store_true", help="Turn the specified relay(s) ON and exit.")
    action.add_argument("--off", action="store_true", help="Turn the specified relay(s) OFF and exit.")
    action.add_argument(
        "--pulse",
        type=float,
        metavar="SECONDS",
        help="Turn relay(s) ON for SECONDS, then OFF (one-shot).",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Do not call GPIO.cleanup() on exit (useful in some embedded flows).",
    )

    args = parser.parse_args()

    relay_hat = None
    try:
        relay_hat = SM16relind.SM16relind(args.stack)

        if args.on:
            for ch in args.relay:
                print(f"Turning relay {ch} ON (stack={args.stack})")
                relay_hat.set(ch, 1)
        elif args.off:
            for ch in args.relay:
                print(f"Turning relay {ch} OFF (stack={args.stack})")
                relay_hat.set(ch, 0)
        elif args.pulse is not None:
            for ch in args.relay:
                print(f"Pulsing relay {ch} ON for {args.pulse:.3f}s (stack={args.stack})")
                relay_hat.set(ch, 1)
            time.sleep(max(0.0, args.pulse))
            for ch in args.relay:
                relay_hat.set(ch, 0)
        print("Done.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        try:
            if relay_hat is not None and args.off:
                # nothing to do; already off
                pass
        except Exception:
            pass
        if not args.no_cleanup:
            # try:
            #     GPIO.cleanup()
            # except Exception:
            #     pass
                pass


if __name__ == "__main__":
    # If no args provided, run the legacy test sequence. Otherwise run the CLI.
    if len(sys.argv) == 1:
        print("Starting relay hat test sequence...")
        test_relay_hat()
    else:
        cli_control()