# I²C cheatsheet

Quick reference for the I²C topology RRR expects.

## Address map

| Device | Default address | Notes |
|---|---|---|
| Sequent Microsystems 16-relay HAT | `0x20–0x27` | Stack level selected via on-board jumpers JP1–JP3. Stack 0 = `0x20`. |
| Sensirion SLF3S-0600F flow sensor | `0x08` | Legacy direct-I²C path; superseded by Teensy UART bridge but still supported as fallback (see [Project/drivers/flow_sensor.py](Project/drivers/flow_sensor.py)). |

If `i2cdetect -y 1` shows neither, the bus itself is the problem — not the
device.

## Stack-level jumpers (16-RELAYS)

| JP1 | JP2 | JP3 | Address | Stack level |
|---|---|---|---|---|
| open | open | open | `0x20` | 0 |
| short | open | open | `0x21` | 1 |
| open | short | open | `0x22` | 2 |
| short | short | open | `0x23` | 3 |

Authoritative reference: [Project/docs/16-RELAYS-UsersGuide_d5e24457-bdd9-4e16-a307-7f90bbd668bb.pdf](Project/docs/16-RELAYS-UsersGuide_d5e24457-bdd9-4e16-a307-7f90bbd668bb.pdf).

## Bus numbers (Pi-version-dependent)

| Pi | User header bus | Notes |
|---|---|---|
| 4 | `/dev/i2c-1` | Stable across releases. |
| 5 | `/dev/i2c-1` (default) | Some early firmware exposed it on `/dev/i2c-13`; the installer pins the right one. |

## When the bus looks dead

1. `dmesg | grep -i i2c` — kernel-level errors?
2. `ls -l /dev/i2c-*` — does the device node exist? (Group should be `i2c`.)
3. `groups` — is your user in the `i2c` group? `scripts/install/50-services.sh` adds
   you; **you must log out and back in for the new group to apply**.
4. `sudo i2cdetect -y 1` — sudo bypass; if this works and the unprivileged
   call doesn't, it's group membership.

## Two devices on one bus — clock conflict

RRR's flow-sensor + relay HAT share bus 1. `I2CCoordinator`
([Project/drivers/i2c_coordinator.py](Project/drivers/i2c_coordinator.py)) holds
a `threading.Lock` around every read/write. Bypassing it causes intermittent
`OSError: [Errno 110]` under load. Always go through the coordinator.
