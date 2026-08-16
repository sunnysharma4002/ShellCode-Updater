from flask import Flask, render_template, request, jsonify, send_file
from io import BytesIO

app = Flask(__name__)

def parse_address(value):
    value = str(value).strip().lower().replace("_", "")
    if not value:
        raise ValueError("Address is required")
    return int(value, 16) if value.startswith("0x") else int(value, 16)

def calculate_bl(bl_address, target_address):
    pc = bl_address + 8
    delta = target_address - pc

    if delta % 4 != 0:
        raise ValueError("BL displacement must be 4-byte aligned")

    imm24 = (delta >> 2) & 0xFFFFFF
    opcode = 0xEB000000 | imm24
    raw = opcode.to_bytes(4, byteorder="little")

    return raw, pc, delta, imm24, opcode

def filename_to_bytes(filename):
    filename = str(filename).strip()

    if not filename:
        raise ValueError("Filename is required")

    if "\x00" in filename:
        raise ValueError("Filename cannot contain a NUL byte")

    try:
        # C-style null-terminated ASCII filename.
        return filename.encode("ascii") + b"\x00"
    except UnicodeEncodeError:
        raise ValueError("Filename must contain ASCII characters only")

def format_bytes(data):
    return ", ".join(f"0x{byte:02X}" for byte in data)

def format_multiline(data, per_line=8):
    lines = []

    for i in range(0, len(data), per_line):
        chunk = data[i:i + per_line]
        comma = "," if i + per_line < len(data) else ""
        lines.append("        " + format_bytes(chunk) + comma)

    return "\n".join(lines)

def build_result(data):
    dlopen = parse_address(data.get("dlopen", ""))
    case10 = parse_address(data.get("case10", ""))
    filename = str(data.get("filename", "")).strip()

    # The reference layout places BL at case10 + 0x10.
    bl_address = case10 + 0x10

    bl_raw, pc, delta, imm24, opcode = calculate_bl(
        bl_address,
        dlopen
    )

    filename_raw = filename_to_bytes(filename)

    prefix = bytes.fromhex(
        "F0 4F 2D E9 "
        "10 00 9F E5 "
        "01 10 A0 E3 "
        "00 00 8F E0"
    )

    suffix = bytes.fromhex(
        "00 00 A0 E3 "
        "F0 8F BD E8"
    )

    complete_payload = prefix + bl_raw + suffix + filename_raw

    # Copyable C++ byte-array output only.
    cpp_array = (
        "BYTE __stb[] = {\n"
        + format_multiline(complete_payload)
        + "\n};"
    )

    return {
        "dlopen": f"0x{dlopen:X}",
        "case10": f"0x{case10:X}",
        "bl_address": f"0x{bl_address:X}",
        "pc": f"0x{pc:X}",
        "delta": f"{delta:+#x}",
        "imm24": f"0x{imm24:06X}",
        "opcode": f"0x{opcode:08X}",

        # IMPORTANT: filename bytes are explicitly returned.
        "filename": filename,
        "filename_bytes": format_bytes(filename_raw),

        "bl_bytes": format_bytes(bl_raw),
        "complete_bytes": format_bytes(complete_payload),
        "cpp_array": cpp_array,
        "payload_length": len(complete_payload)
    }

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/generate")
def generate():
    try:
        data = request.get_json(force=True)
        result = build_result(data)
        return jsonify({"ok": True, **result})
    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)
        }), 400

@app.post("/download")
def download():
    try:
        data = request.get_json(force=True)
        result = build_result(data)

        output = result["cpp_array"].encode("utf-8")
        stream = BytesIO(output)
        stream.seek(0)

        return send_file(
            stream,
            mimetype="text/plain",
            as_attachment=True,
            download_name="generated_bytes.cpp"
        )
    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)
        }), 400

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
