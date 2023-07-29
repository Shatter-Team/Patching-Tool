"""
libsmashhit patcher tool
"""

import tkinter
import tkinter.ttk as ttk
import tkinter.messagebox
import tkinter.filedialog
import json
import os
import sys
import struct

VERSION = (0, 4, 0)

class File():
	"""
	A libsmashhit.so file
	"""
	
	def __init__(self, path):
		"""
		Initialise the file
		"""
		
		self.file = open(path, "rb+")
	
	def read(self, location):
		"""
		Read 32 bits from the given location
		"""
		
		self.file.seek(location, 0)
		return self.file.read(4)
	
	def patch(self, location, data):
		"""
		Write patched data to the file
		"""
		
		self.file.seek(location, 0)
		self.file.write(data)
	
	def __del__(self):
		"""
		Destroy the file
		"""
		
		self.file.close()

class Patcher:
	"""
	Instance of a patching tool
	"""
	
	def __init__(self):
		self.patches = {}
		self.buttons = {}
	
	def add(self, name, desc, func, default = False, value = False):
		"""
		Add a patch to the list of patches
		"""
		
		self.patches[name] = {
			"desc": desc,
			"func": func,
			"default": default,
			"value": value,
		}
	
	def getFunc(self, name):
		"""
		Get the patch function to call
		"""
		
		return self.patches[name]["func"]
	
	def render(self, w):
		"""
		Add everything to the window
		"""
		
		for p in self.patches:
			self.buttons[p] = w.checkbox(self.patches[p]["desc"], default = self.patches[p]["default"])
			
			# Also show the textbox if we need it
			if (self.patches[p]["value"]):
				self.buttons[f"{p}_val"] = w.textbox(True)
			
			# Next element (for two row layout)
			w.next()
	
	def getData(self):
		"""
		Get the options that the user has selected
		"""
		
		data = {}
		
		for k in self.buttons:
			data[k] = self.buttons[k].get()
		
		return data

gPatcher = Patcher()

def patch_const_mov_instruction_arm64(old, value):
	mask = 0b11100000111111110001111100000000
	
	old = old & (~mask)
	
	last = (value & 0b111) << 29
	first = ((value >> 3) & 0b11111111) << 16
	new = last | first
	
	return (old | new)

def patch_const_subs_instruction_arm64(old, value):
	mask = 0b00000000111111000011111100000000
	
	old = old & (~mask)
	
	last = (value & 0b111111) << 18
	first = ((value >> 6) & 0b111111) << 8
	new = last | first
	
	return (old | new)

def patch_antitamper(f, value):
	f.patch(0x47130, b"\x1f\x20\x03\xd5")
	f.patch(0x474b8, b"\x3e\xfe\xff\x17")
	f.patch(0x47464, b"\x3a\x00\x00\x14")
	f.patch(0x47744, b"\x0a\x00\x00\x14")
	f.patch(0x4779c, b"\x1f\x20\x03\xd5")
	f.patch(0x475b4, b"\xff\xfd\xff\x17")
	f.patch(0x46360, b"\x13\x00\x00\x14")

gPatcher.add(
	name = "antitamper",
	desc = "Disable anti-tamper protection (required)",
	func = patch_antitamper,
	default = True,
)

def patch_premium(f, value):
	tkinter.messagebox.showwarning("Software copyright notice", "APKs where premium is patched should NOT be distrubuted, and this functionality is only available for users to extercise their right to modify software that they own for private use. If you do not own premium, you should delete the patched file immediately.")
	
	f.patch(0x5ace0, b"\x1f\x20\x03\xd5")
	f.patch(0x598cc, b"\x14\x00\x00\x14")
	f.patch(0x59720, b"\xa0\xc2\x22\x39")
	f.patch(0x58da8, b"\x36\x00\x00\x14")
	f.patch(0x57864, b"\xbc\x00\x00\x14")
	f.patch(0x566ec, b"\x04\x00\x00\x14")

gPatcher.add(
	name = "premium",
	desc = "Enable premium by default",
	func = patch_premium,
)

def patch_encryption(f, value):
	f.patch(0x567e8, b"\xc0\x03\x5f\xd6")
	f.patch(0x5672c, b"\xc0\x03\x5f\xd6")

gPatcher.add(
	name = "encryption",
	desc = "Disable save file encryption",
	func = patch_encryption,
)

def patch_key(f, value):
	if (not value):
		tkinter.messagebox.showwarning("Change key warning", "The encryption key will be set to Smash Hit's default key, 5m45hh1t41ght, since you did not set one.")
		value = "5m45hh1t41ght"
	
	key = value.encode('utf-8')
	
	if (len(key) >= 24):
		tkinter.messagebox.showwarning("Change key warning", "Your encryption key is longer than 23 bytes, so it has been truncated.")
		key = key[:23]
	
	f.patch(0x1f3ca8, key + (b"\x00" * (24 - len(key))))

gPatcher.add(
	name = "encryption_key",
	desc = "Change encryption key to:",
	func = patch_key,
	value = True,
)

def patch_balls(f, value):
	if (not value):
		tkinter.messagebox.showerror("Patch balls error", "You didn't put in a value for how many balls you want to start with. Balls won't be patched!")
		return
	
	value = int(value)
	
	# Somehow, this works.
	d = struct.unpack(">I", f.read(0x57cf4))[0]
	f.patch(0x57cf4, struct.pack(">I", patch_const_mov_instruction_arm64(d, value)))
	
	f.patch(0x57ff8, struct.pack("<I", value))

gPatcher.add(
	name = "balls",
	desc = "Change starting ballcount to:",
	func = patch_balls,
	value = True,
)

def patch_hit(f, value):
	if (not value):
		tkinter.messagebox.showerror("Patch drop balls error", "You didn't put in a value for how many balls you want to drop when you hit something. Dropping balls won't be patched!")
		return
	
	value = int(value)
	
	# Patch the number of balls to subtract from the score
	d = struct.unpack(">I", f.read(0x715f0))[0]
	f.patch(0x715f0, struct.pack(">I", patch_const_subs_instruction_arm64(d, value)))
	
	# Patch the number of balls to drop
	d = struct.unpack(">I", f.read(0x71624))[0]
	f.patch(0x71624, struct.pack(">I", patch_const_mov_instruction_arm64(d, value)))
	
	# This changes from "cmp w23,#0xa" to "cmp w23,w1" so that we don't
	# need to make a specific patch for the comparision.
	f.patch(0x7162c, b"\xff\x02\x01\x6b")

gPatcher.add(
	name = "hit",
	desc = "Change crash ball loss to:",
	func = patch_hit,
	value = True,
)

def patch_fov(f, value):
	if (not value):
		tkinter.messagebox.showerror("Patch FoV error", "You didn't put in a value for the FoV you want. FoV won't be patched!")
		return
	
	f.patch(0x1c945c, struct.pack("<f", float(value)))

gPatcher.add(
	name = "fov",
	desc = "Change field of view to:",
	func = patch_fov,
	value = True,
)

def patch_seconds(f, value):
	value = float(value) if value else ""
	
	if (not value):
		tkinter.messagebox.showwarning("Patch room length in seconds warning", "You didn't put in a room length in seconds. Room length in seconds will be set to the default! (32)")
		value = 32.0
	
	tkinter.messagebox.showwarning("Patch room length in seconds warning", f"Changing the time a room takes breaks the game if you have improperly lengthed music. Music tracks must now be {value + 4} seconds long.")
	
	# Smash Hit normalises the value to the range [0.0, 1.0] so we need to take the inverse
	f.patch(0x73f80, struct.pack("<f", 1 / value))

gPatcher.add(
	name = "seconds",
	desc = "Change time per room in seconds to:",
	func = patch_seconds,
	value = True,
)

def patch_hitsomething(f, value):
	f.patch(0x71574, b"\xc0\x03\x5f\xd6")

gPatcher.add(
	name = "hitsomething",
	desc = "Remove penalty for hitting obstacles (no clip)",
	func = patch_hitsomething,
)

def patch_trainingballs(f, value):
	f.patch(0x6ba5c, b"\x06\x00\x00\x14")

gPatcher.add(
	name = "trainingballs",
	desc = "Remove ball limit in training mode",
	func = patch_trainingballs,
)

def patch_realpaths_segments(f, value):
	f.patch(0x2119f8, b"\x00")

gPatcher.add(
	name = "realpaths_segments",
	desc = "Use full paths for segments",
	func = patch_realpaths_segments,
)

def patch_realpaths_obstacles(f, value):
	f.patch(0x211930, b"\x00")

gPatcher.add(
	name = "realpaths_segments",
	desc = "Use full paths for obstacles",
	func = patch_realpaths_obstacles,
)

def patch_realpaths_other(f, value):
	f.patch(0x2118e8, b"\x00")
	f.patch(0x1f48c0, b"\x00")

gPatcher.add(
	name = "realpaths_other",
	desc = "Use full paths for rooms and levels",
	func = patch_realpaths_other,
)

def patch_ads(f, value):
	if (len(value) != 5):
		tkinter.messagebox.showerror("Ads error", "The mod ID is invalid.")
		return
	
	value = value.encode('utf-8')
	
	f.patch(0x2129a0, b"http://smashhitlab.000webhostapp.com/\x00")
	f.patch(0x2129c8, b"ads.php?id=" + value + b"&x=\x00")

gPatcher.add(
	name = "ads",
	desc = "Use Smash Hit Lab mod services",
	func = patch_ads,
	value = True,
)

def patch_os_package_io(f, value):
	### This was the THIRD ATTEMPT to make it work.
	# It works by chaining it on after luaopen_base
	# This one worked, even if its the worst hack :D
	
	f.patch(0xa71b8, b"\xe0\x03\x13\xaa") # Preserve param_1
	f.patch(0xa71c8, b"\xb8\x0e\x00\x14") # Chain to luaopen_package
	f.patch(0xaaef4, b"\xe0\x03\x13\xaa") # Preserve param_1
	f.patch(0xaaf08, b"\xb1\xf0\xff\x17") # Chain to luaopen_io
	f.patch(0xa748c, b"\xe0\x03\x13\xaa") # Preserve param_1
	f.patch(0xa74a0, b"\xd1\xfe\xff\x17") # Chain to luaopen_os
	f.patch(0xa7004, b"\xa0\x00\x80\x52") # Set return to 5 (2 + 1 + 1 + 1 = 5)
	f.patch(0xa7010, b"\xc0\x03\x5f\xd6") # Make sure last is return (not really needed)

gPatcher.add(
	name = "modules1",
	desc = "Enable lua's os and io modules",
	func = patch_os_package_io,
)

def patch_vertical(f, value):
	f.patch(0x46828, b"\x47\x00\x00\x14") # Patch an if (gWidth < gHeight)
	f.patch(0x4693c, b"\x71\x00\x00\x14") # Another if ...
	f.patch(0x46a48, b"\x1f\x20\x03\xd5")

gPatcher.add(
	name = "vertical",
	desc = "Allow running in vertical resolutions",
	func = patch_vertical,
)

def patch_multiplayer_length(f, value):
	# Patch to use length property instead of 200 in versus/co-op
	f.patch(0x6b6d4, b"\x1f\x20\x03\xd5")

gPatcher.add(
	name = "multiplayer_length",
	desc = "Enable mgLength in multiplayer mode",
	func = patch_multiplayer_length,
)

def patch_nofpfix(f, value):
	f.patch(0x72564, b"\x1f\x20\x03\xd5")

gPatcher.add(
	name = "nofpfix",
	desc = "Disable resetting camera position",
	func = patch_nofpfix,
)

def applyPatches(location, patches):
	"""
	Apply patches to a given libsmashhit.so file
	"""
	
	f = File(location)
	
	ver = (f.read(0x1f38a0) + f.read(0x1f38a4))[:5].decode("utf-8")
	
	if (ver != '1.4.2' and ver != '1.4.3'):
		raise Exception(f"Sorry, this doesn't seem to be version 1.4.2 or version 1.4.3 for ARM64 devices. Make sure you have selected the ARM64 libsmashhit.so from 1.4.2 or 1.4.3 and try again.")
	
	# For each patch ...
	for p in patches:
		# ... that is actually a patch and is wanted ...
		if (not p.endswith("_val") and patches[p] == True):
			# ... do the patch, also passing (PATCHNAME) + "_val" if it exists.
			(gPatcher.getFunc(p))(f, patches.get(p + "_val", None))

# ==============================================================================
# ==============================================================================

class Window():
	"""
	Window thing
	"""
	
	def __init__(self, title, size, class_name = "Application"):
		"""
		Initialise the window
		"""
		
		self.window = tkinter.Tk(className = class_name)
		self.window.title(title)
		self.window.geometry(size)
		
		self.position = -25
		self.gap = 35
		self.current = 0
		
		# HACK to make the things to into two rows
		self.count = 0
		
		# Main frame
		ttk.Frame(self.window)
	
	def getYPos(self, flush = False):
		self.position += self.gap if not flush and (self.count % 2 == 0) else 0
		
		return self.position
	
	def getXPos(self):
		return 20
	
	def getExtraXPos(self):
		# for the hack
		return (515 + self.getXPos()) * (self.count % 2)
	
	def label(self, content):
		"""
		Create a label
		"""
		
		label = tkinter.Label(self.window, text = content)
		label.place(x = self.getXPos(), y = self.getYPos())
		
		return label
	
	def button(self, content, action, *, extraY = 0, absY = None):
		button = tkinter.Button(self.window, text = content, command = action)
		button.place(x = self.getXPos(), y = (self.getYPos() + extraY) if not absY else absY)
		
		return button
	
	def textbox(self, inline = False):
		"""
		Create a textbox
		"""
		
		entry = tkinter.Entry(self.window, width = (70 if not inline else 28))
		
		if (not inline):
			entry.place(x = self.getXPos() + self.getExtraXPos(), y = self.getYPos())
		else:
			entry.place(x = (self.getXPos() + 290) + self.getExtraXPos(), y = self.getYPos(True))
		
		return entry
	
	def checkbox(self, content, default = False):
		"""
		Create a tickbox
		"""
		
		var = tkinter.IntVar()
		
		tick = tkinter.Checkbutton(self.window, text = content, variable = var, onvalue = 1, offvalue = 0)
		tick.place(x = self.getXPos() + self.getExtraXPos(), y = self.getYPos())
		
		var.set(1 if default else 0)
		
		# self.count += 1
		
		return var
	
	def next(self):
		self.count += 1
	
	def main(self):
		self.window.mainloop()

def gui(default_path = None):
	w = Window(f"Smash Hit Tweak Tool v{VERSION[0]}.{VERSION[1]}.{VERSION[2]}", "1100x500")
	
	w.label("You can use this tool to apply common tweaks to Smash Hit's main binary. (Only compatible with v1.4.2 and v1.4.3 on ARM64.)")
	
	location = default_path
	
	if (not location):
		location = tkinter.filedialog.askopenfilename(title = "Pick libsmashhit.so", filetypes = (("Shared objects", "*.so"), ("All files", "*.*")))
	
	w.label("If you have issues typing in boxes, try clicking off and on the window first.")
	w.label("Please select what patches you would like to apply:")
	
	gPatcher.render(w)
	
	def x():
		"""
		Callback to run when the "Patch libsmashhit.so!" button is clicked
		"""
		
		try:
			patches = gPatcher.getData()
			
			applyPatches(location.get() if type(location) != str else location, patches)
			
			tkinter.messagebox.showinfo("Success", "Your libsmashhit has been patched succesfully!")
		
		except Exception as e:
			tkinter.messagebox.showerror("Error", str(e))
	
	w.button("Patch game binary!", x, absY = 500 - 60)
	
	w.main()

def main():
	try:
		gui(sys.argv[1] if len(sys.argv) >= 2 else None)
	except Exception as e:
		tkinter.messagebox.showerror("Fatal error", str(e))

if (__name__ == "__main__"):
	main()
