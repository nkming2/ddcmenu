#!/usr/bin/env python3
import json
import re
import subprocess

class DetectParser:
	DISPLAY_PATTERN = re.compile("Display ([0-9])")
	ITEM_PATTERN = re.compile("   (.+?): *(.+?)")
	ITEM_GROUP_PATTERN = re.compile("   (.+?):")
	ITEM_GROUP_ITEM_PATTERN = re.compile("      (.+?): *(.+?)")

	def __init__(self, input):
		self._in = input.split("\n")

	def parse(self):
		self._i = 0
		products = []
		while self._i < len(self._in):
			l = self._pop_line()
			m = self.DISPLAY_PATTERN.fullmatch(l)
			if m is None:
				continue
			products += [self._parse_display(m)]
		return products

	def _parse_display(self, m):
		product = {}
		product["Display"] = int(m[1])

		def _parse_next(l):
			item_m = self.ITEM_PATTERN.fullmatch(l)
			if item_m is not None:
				return self._parse_item(item_m)
			group_m = self.ITEM_GROUP_PATTERN.fullmatch(l)
			if group_m is not None:
				return self._parse_item_group(group_m)
			return None

		while self._i < len(self._in):
			l = self._pop_line()
			d = _parse_next(l)
			if d:
				product.update(d)
			else:
				self._revert_line()
				return product
		return product

	def _parse_item(self, m):
		return {m[1]: m[2]}

	def _parse_item_group(self, m):
		d = {}
		product = {m[1]: d}
		while self._i < len(self._in):
			l = self._pop_line()
			item_m = self.ITEM_GROUP_ITEM_PATTERN.fullmatch(l)
			if item_m is not None:
				d.update(self._parse_item(item_m))
			else:
				self._revert_line()
				return product
		return product

	def _pop_line(self):
		l = self._in[self._i]
		self._i += 1
		return l

	def _revert_line(self):
		self._i -= 1

class CapabilitiesParser:
	TOPIC_PATTERN = re.compile("VCP Features:")
	FEATURE_PATTERN = re.compile("   Feature: ([0-9A-F]{2}) \((.+)\)")
	FEATURE_DESCRIPTION_PATTERN = re.compile("      (.+)")

	def __init__(self, input):
		self._in = input.split("\n")

	def parse(self):
		self._i = 0
		while self._i < len(self._in):
			l = self._pop_line()
			m = self.TOPIC_PATTERN.fullmatch(l)
			if m is None:
				continue
			product = self._parse_topic(m)
			if product is not None:
				return product
		return None

	def _parse_topic(self, m):
		product = []
		while self._i < len(self._in):
			l = self._pop_line()
			m = self.FEATURE_PATTERN.fullmatch(l)
			if m is None:
				self._revert_line()
				return product
			product += [self._parse_feature(m)]
		return product

	def _parse_feature(self, m):
		product = {
			"id": m[1],
			"label": m[2],
		}

		# look for value description
		description = []
		while self._i < len(self._in):
			l = self._pop_line()
			description_m = self.FEATURE_DESCRIPTION_PATTERN.fullmatch(l)
			if description_m is not None:
				description += [description_m[1]]
			else:
				self._revert_line()
				break
		if description:
			product["description"] = "\n".join(description)
		return product

	def _pop_line(self):
		l = self._in[self._i]
		self._i += 1
		return l

	def _revert_line(self):
		self._i -= 1

class GetvcpParser:
	def __init__(self, input):
		self._in = input

	def parse(self):
		return self._in.strip().split("): ")[-1]

class Ddc:
	@staticmethod
	def detect():
		out = subprocess.check_output([
			"ddcutil",
			"detect",
		]).decode("utf8")
		return DetectParser(out).parse()

	@staticmethod
	def capabilities(display):
		out = subprocess.check_output([
			"ddcutil",
			"capabilities",
			"-d",
			str(display),
		]).decode("utf8")
		return CapabilitiesParser(out).parse()

	@staticmethod
	def getvcp(display, id):
		out = subprocess.check_output([
			"ddcutil",
			"getvcp",
			"-d",
			str(display),
			str(id),
		]).decode("utf8")
		return GetvcpParser(out).parse()

	@staticmethod
	def setvcp(display, id, value):
		subprocess.check_output([
			"ddcutil",
			"setvcp",
			"-d",
			str(display),
			str(id),
			str(value),
		]).decode("utf8")

if __name__ == "__main__":
	print("Use at your own risk")
	displays = Ddc.detect()
	a = True
	while a:
		a = False
		try:
			print("\nDetected displays:")
			for i, d in enumerate(displays):
				print(f"{i}) {d['EDID synopsis']['Model']}")
			d_pick = int(input("Select a display: "))
			d = displays[d_pick]
			print(f"Selected \"{d['EDID synopsis']['Model']}\"")

			print("\nQuerying capabilities...")
			capabilities = Ddc.capabilities(d["Display"])
			print("Capabilities:")
			for c in capabilities:
				print(f"{c['id']}) {c['label']}")
			c_pick = input("Select a capability: ")
			try:
				c = next(c for c in capabilities if c["id"] == c_pick)
			except StopIteration:
				print("Invalid input. Beware that you must enter the feature code exactly as displayed (including the leading zeros if any)")
				continue
			print(f"Selected \"{c['label']}\"")
			if "description" in c:
				print(c["description"])

			print("\nQuerying feature...")
			try:
				value = Ddc.getvcp(d["Display"], c["id"])
			except subprocess.CalledProcessError as e:
				print(f"Failed with return code {e.returncode}")
				if e.stdout is not None:
					print(e.stdout.decode("utf8").strip())
				continue
			print(f"Return: {value}")
			set_value = input("Set new value: ")
			if set_value:
				Ddc.setvcp(d["Display"], c["id"], set_value)
		except KeyboardInterrupt:
			print()
			exit(0)
		except Exception as e:
			print(e)
