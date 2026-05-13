# Rodent Refreshment Regulator - Quick Reference Guide

This quick reference guide covers the most common tasks and troubleshooting tips for the Rodent Refreshment Regulator (RRR) system. For more detailed information, refer to the in-app Help tab.

## Common Tasks

### 🐭 Animal Management

| Task | How To Do It |
|------|--------------|
| Add a new animal | Animals tab → Add Animal → Fill details → Save |
| Edit animal info | Animals tab → Select animal → Edit → Update details → Save |
| Update weight | Animals tab → Select animal → Edit → Enter new weight → Save |
| Remove animal | Animals tab → Select animal → Delete → Confirm |

### 📆 Schedule Management

| Task | How To Do It |
|------|--------------|
| Create schedule | Wizard tab (or "+ New Schedule" in Schedules hub) → Step 1–4 → Save |
| Edit schedule | Schedules tab → card menu → Edit → Update → Save |
| Delete schedule | Schedules tab → card menu → Delete (or multi-select → bulk delete) |
| Assign animals to cages | Inside the Wizard, Step 2 — multi-select from the available list |
| View schedule details | Schedules tab → card **Info** button |

### 🔢 Cage Management

| Task | How To Do It |
|------|--------------|
| Rename a cage | Cages tab → click cage tile → enter custom name → Save |
| View relay layout | Cages tab — shows the full HAT board with master vs. animal relays |

### ⚙️ System Operations

| Task | How To Do It |
|------|--------------|
| Start water delivery | Drag schedule card onto Run/Stop drop area → Run Program |
| Stop water delivery | Stop Program |
| Monitor a live run | Execution Monitor tab appears next to Terminal during a run |
| Test relays | Settings → Delivery → Test Relay → select relay → Run Test |
| Calibrate pumps/valves | Settings → Calibration → Run Calibration Wizard |
| Prime tubing | Settings → Priming → Run priming sequence |
| Set up notifications | Settings → General → Slack credentials → Save |

## Troubleshooting Guide

### Water Delivery Issues

| Problem | Solution |
|---------|----------|
| No water delivered | • Check if program is running<br>• Ensure time window is correct<br>• Check water reservoir level<br>• Verify pump connections |
| Uneven water delivery | • Calibrate pumps<br>• Check for air bubbles in tubing<br>• Run 200 test triggers to prime pumps |
| Leaking connections | • Check tube fittings<br>• Replace damaged tubing<br>• Ensure correct tube diameter (2mm) |

### Software Issues

| Problem | Solution |
|---------|----------|
| Application won't start | • Restart your Raspberry Pi<br>• Run `./start_rrr.sh` from terminal to see error messages |
| Can't save settings | • Log in with a user account (not guest mode)<br>• Check file permissions |
| Slack notifications not working | • Verify internet connection<br>• Check Slack credentials<br>• Ensure channel ID is correct |

### Hardware Issues

| Problem | Solution |
|---------|----------|
| Relay HAT not detected | • Check physical connections<br>• Verify DIP switch settings<br>• Restart the system |
| Pump not triggering | • Test the relay<br>• Check power connections<br>• Verify common ground connection |
| System freezes during operation | • Check for overheating<br>• Ensure power supply is adequate<br>• Reduce number of simultaneous triggers |

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+R` | Run program |
| `Ctrl+S` | Stop program |
| `Ctrl+H` | Open help |
| `Ctrl+L` | Show logs |
| `Ctrl+Tab` | Switch between tabs |
| `Esc` | Close popup dialogs |

## Daily Checklist

### Morning Setup
- [ ] Check water reservoir level and refill if needed
- [ ] Inspect tubing for leaks or blockages
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
- Lab Manager: [lab.manager@example.com](mailto:lab.manager@example.com)

For application issues, report through the Help tab in the application.

---

**Remember**: The Help tab in the application provides more detailed information on all features. Use the search function to quickly find specific topics. 