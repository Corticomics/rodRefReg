# Rodent Refreshment Regulator - Quick Reference Guide

This quick reference guide covers the most common tasks and troubleshooting tips for the Rodent Refreshment Regulator (RRR) system. For more detailed information, refer to the in-app Help tab.

## Common Tasks

### Animal Management

| Task | How To Do It |
|------|--------------|
| Add a new animal | Animals tab → Add Animal → Fill details → Save |
| Edit animal info | Animals tab → Select animal → Edit → Update details → Save |
| Update weight | Animals tab → Select animal → Edit → Enter new weight → Save |
| Remove animal | Animals tab → Select animal → Delete → Confirm |

### Schedule Management

| Task | How To Do It |
|------|--------------|
| Create schedule | Wizard tab (or "+ New Schedule" in Schedules hub) → Step 1–4 → Save |
| Edit schedule | Schedules tab → card menu → Edit → Update → Save |
| Delete schedule | Schedules tab → card menu → Delete (or multi-select → bulk delete) |
| Assign animals to cages | Inside the Wizard, Step 2 — multi-select from the available list |
| View schedule details | Schedules tab → card **Info** button |

### Cage Management

| Task | How To Do It |
|------|--------------|
| Rename a cage | Cages tab → double-click the cage tile → type the name → Enter (Esc cancels; relay 16 cannot be renamed) |
| View relay layout | Cages tab — shows the full HAT board: relay 16 is the MASTER SOLENOID on a shared-manifold rig and RESERVED (unused) on an independent rig |

### System Operations

| Task | How To Do It |
|------|--------------|
| Start water delivery | Drag schedule card onto Run/Stop drop area → **Run**. In solenoid pulse mode (the default), Run refuses a schedule that waters a cage with no usable calibration measured under this device's valve topology (*Valve calibration needed*): calibrate the listed cages first |
| Stop water delivery | **Stop**. If it shows *Relays Not Confirmed Off*, disconnect the valve power supply, then check the relay HAT and its I²C connection |
| Monitor a live run | Execution Monitor tab appears next to Terminal during a run |
| Test a valve | Settings → Priming → select the cage → **Open Selected**, then **Close Selected** (on a shared-manifold rig click **Open Master** first and **Close Master** after) |
| Calibrate valves | Settings → Calibration → **Calibrate** on the cage's row (or **Calibrate All Uncalibrated**) |
| Prime tubing | Settings → Priming → select cage → **Open Selected** → **Close Selected** once water flows (on a shared-manifold rig click **Open Master** first and **Close Master** after) |
| Change valve topology | Settings → Delivery → Valve Topology (logged in; refused while a schedule, priming or calibration runs). Priming cannot open a valve until RRR is closed and reopened; then recalibrate the cages marked Stale |
| Set up notifications | Settings → General → Slack Integration → enter the Slack Bot Token and Channel ID (each is saved when you press Enter or leave the field, and is used from the next message) |

## Troubleshooting Guide

### Water Delivery Issues

| Problem | Solution |
|---------|----------|
| No water delivered | • Check if the schedule is running (Run may have refused it: *Valve calibration needed* lists the cages to calibrate)<br>• Ensure time window is correct<br>• Look in the Terminal tab for `[VALVE ERROR]`: the line says why the delivery stopped, most often a valve command that did not reach its relay HAT<br>• Check the water reservoir level, or on an independent rig that animal's syringe and line<br>• Verify pump connections (pump mode) |
| Uneven water delivery | • Check for air bubbles in tubing: prime the line (Settings → Priming)<br>• Solenoid rig: recalibrate that cage (Settings → Calibration → **Recalibrate** on its row)<br>• Pump mode: calibrate the pumps and run 200 test triggers to prime them |
| Leaking connections | • Check tube fittings<br>• Replace damaged tubing<br>• Ensure correct tube diameter (2mm) |

### Software Issues

| Problem | Solution |
|---------|----------|
| Application won't start | • Restart your Raspberry Pi<br>• Run `~/.local/bin/rrr` from a terminal to see error messages (where RRR runs as the user service: `journalctl --user -u rrr.service -n 50`) |
| Can't save settings | • Log in with a user account (not guest mode)<br>• Check file permissions |
| Slack notifications not working | • Verify internet connection<br>• Check Slack credentials<br>• Ensure channel ID is correct |

### Hardware Issues

| Problem | Solution |
|---------|----------|
| Relay HAT not detected | • Check physical connections and `sudo i2cdetect -y 1`<br>• Verify the stack-level jumpers<br>• After fixing it, close and reopen RRR: until then every valve delivery to a missing HAT fails with `[VALVE ERROR]` |
| `[VALVE CRITICAL] … OPEN`, *Emergency Stop Failed* or *Relays Not Confirmed Off* | • Disconnect the valve power supply first<br>• Then check the relay HAT and its I²C connection; Settings → Priming → CLOSE ALL RELAYS switches every relay off again and stops a running schedule (it does not resume: Run starts it over, so check what each animal has received first)<br>• `[VALVE OK] … closed after all` means a later close got through and that alarm is cleared |
| Pump not triggering | • Test the relay<br>• Check power connections<br>• Verify common ground connection |
| System freezes during operation | • Check for overheating<br>• Ensure power supply is adequate<br>• Reduce number of simultaneous triggers |

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+F` or `F3` | Help tab: jump to the search bar |
| `Ctrl+Tab` | Switch between tabs |
| `Esc` | Close popup dialogs; in the Help tab clear the search; in the Cages tab cancel a rename |

Run and Stop have no keyboard shortcut: use the **Run** and **Stop** buttons.

## Daily Checklist

### Morning Setup
- [ ] Check water reservoir level (on an independent rig, every animal's syringe) and refill if needed
- [ ] Inspect tubing for leaks or blockages; on an independent rig check every syringe line daily; a primed line holds about three days, so prime again any line left idle over a long weekend
- [ ] Update animal weights
- [ ] Verify schedule for the day
- [ ] Start the program

### Evening Closeout
- [ ] Review water delivery logs
- [ ] Check animal hydration status
- [ ] Clean any soiled tubing
- [ ] Prepare schedule for next day if needed

## Contact Information

For technical support, contact:
- Lab Tech: [Jose Paulo](mailto:josepaulo.pereirajun@ucalgary.ca)

For application issues, report through the Help tab in the application.

---

**Remember**: The Help tab in the application provides more detailed information on all features. Use the search function to quickly find specific topics. 