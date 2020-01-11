#!/usr/bin/env python3
import json
import subprocess

class DetectParser:
	def __init__(self, input):
		self._in = input.split("\n")

	def parse(self):
		self._i = 0
		products = []
		while self._i < len(self._in):
			l = self._peek_line()
			if not l or l.startswith(" "):
				self._i += 1
				continue
			p = self._parse_header()
			if p is not None:
				products += [p]
		return products

	def _parse_header(self):
		l = self._pop_line()
		if not l.startswith("Display"):
			return None

		product = {}
		product["Display"] = int(l.split(" ")[1])
		while self._i < len(self._in):
			l2 = self._peek_line()
			if not l2.startswith("   "):
				return product
			d = self._parse_items(3)
			if d:
				product.update(d)
		return product

	def _parse_items(self, indentation):
		l = self._pop_line()[indentation:]
		pair = self._parse_line(l)
		product = {pair[0]: pair[1]}

		if isinstance(pair[1], dict):
			while self._i < len(self._in):
				l2 = self._peek_line()
				next_indentation = indentation + 3
				if not l2.startswith(" " * next_indentation):
					return product
				d = self._parse_items(next_indentation)
				if d:
					pair[1].update(d)
		return product

	def _parse_line(self, l):
		pair = l.split(":")
		key = pair[0]
		value = pair[1].strip()
		if not value:
			value = {}
		return (key, value)

	def _pop_line(self):
		l = self._in[self._i]
		self._i += 1
		return l

	def _peek_line(self):
		return self._in[self._i]

class CapabilitiesParser:
	def __init__(self, input):
		self._in = input.split("\n")

	def parse(self):
		self._i = 0
		while self._i < len(self._in):
			l = self._peek_line()
			if not l or l.startswith(" "):
				self._pop_line()
				continue
			product = self._parse_topic()
			if product is not None:
				return product
		return None

	def _parse_topic(self):
		l = self._pop_line()
		if not l.startswith("VCP Features:"):
			return None

		productd = []
		while self._i < len(self._in):
			l = self._peek_line()
			if not l.startswith("   "):
				return productd
			d = self._parse_feature()
			if d:
				productd += [d]
		return productd

	def _parse_feature(self):
		l = self._pop_line()[3:]
		if not l.startswith("Feature: "):
			return None
		pair = l.split(" ")[1:]
		product = {
			"id": pair[0],
			"label": " ".join(pair[1:])[1:-1],
		}

		# look for value description
		description = []
		while self._i < len(self._in):
			l2 = self._peek_line()
			if l2.startswith("      "):
				self._i += 1
				description += [l2[6:]]
			else:
				break
		if description:
			product["description"] = "\n".join(description)
		return product

	def _pop_line(self):
		l = self._in[self._i]
		self._i += 1
		return l

	def _peek_line(self):
		return self._in[self._i]

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
	def getvcp(id):
		out = subprocess.check_output([
			"ddcutil",
			"getvcp",
			str(id),
		]).decode("utf8")
		return GetvcpParser(out).parse()

	@staticmethod
	def setvcp(id, value):
		subprocess.check_output([
			"ddcutil",
			"setvcp",
			str(id),
			str(value),
		]).decode("utf8")

if __name__ == "__main__":
	print("Use at your own risk")
	displays = Ddc.detect()
	while True:
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
				value = Ddc.getvcp(c["id"])
			except subprocess.CalledProcessError as e:
				print(f"Failed with return code {e.returncode}")
				if e.stdout is not None:
					print(e.stdout.decode("utf8").strip())
				continue
			print(f"Return: {value}")
			set_value = input("Set new value: ")
			if set_value:
				Ddc.setvcp(c["id"], set_value)
		except KeyboardInterrupt:
			print()
			exit(0)
		except Exception as e:
			print(e)
