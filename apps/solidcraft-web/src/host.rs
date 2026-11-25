//! File exchange with a host page (`?embed=editor`): the page hands the editor a file with
//! `host.write_file` and takes one back with `host.read_file`, both on the browser's virtual file
//! system under `/host/`, where the insert, import and export commands read and write by path.
//!
//! ```js
//! await app.request("host.write_file", {path: "/host/part.step", base64}); // {path, bytes}
//! await app.execute("file.insert_step", {path: "/host/part.step"});
//! await app.execute("file.export_step", {path: "/host/out.step"});
//! await app.request("host.read_file", {path: "/host/out.step"});           // {path, bytes, base64}
//! ```
//!
//! Only a single plain file name under `/host/` is accepted (at most [`MAX_NAME_CHARS`]
//! characters, no `/`, `\`, `..` or control characters), and at most [`MAX_BYTES`] per file.
//! The two methods are answered here, in the page, without going through the control channel:
//! their base64 may be larger than the channel's 16 MiB JSON limit.

use base64::Engine as _;
use base64::engine::general_purpose::STANDARD;

/// The folder a host page reads and writes.
pub const PREFIX: &str = "/host/";
/// Largest file a host page may write or read, decoded.
pub const MAX_BYTES: usize = 64 << 20;
/// Longest file name after [`PREFIX`], in characters.
pub const MAX_NAME_CHARS: usize = 120;

/// The path, when it names a single plain file under `/host/`.
pub fn check_path(path: &str) -> Result<&str, String> {
    let Some(name) = path.strip_prefix(PREFIX) else {
        return Err(format!("host files must be under {PREFIX} (got {path:?})"));
    };
    if name.is_empty() {
        return Err(format!("host file path {path:?} has no file name"));
    }
    if name.chars().count() > MAX_NAME_CHARS {
        return Err(format!("host file name is longer than {MAX_NAME_CHARS} characters"));
    }
    if name.contains('/') || name.contains('\\') {
        return Err(format!("host file path {path:?} must name a single file directly under {PREFIX}"));
    }
    if name == "." || name == ".." || name.contains("..") {
        return Err(format!("host file path {path:?} must not contain \"..\""));
    }
    if name.chars().any(char::is_control) {
        return Err("host file name must not contain control characters".into());
    }
    Ok(path)
}

/// Decoded `text`, refused before decoding when it would be over [`MAX_BYTES`].
pub fn decode(text: &str) -> Result<Vec<u8>, String> {
    // Every 4 characters make at most 3 bytes.
    if text.len() / 4 * 3 > MAX_BYTES + 2 {
        return Err(format!("host file is larger than {} MiB", MAX_BYTES >> 20));
    }
    let bytes = STANDARD.decode(text.trim()).map_err(|e| format!("base64 is not valid: {e}"))?;
    if bytes.len() > MAX_BYTES {
        return Err(format!("host file is larger than {} MiB", MAX_BYTES >> 20));
    }
    Ok(bytes)
}

pub fn encode(bytes: &[u8]) -> String {
    STANDARD.encode(bytes)
}

#[cfg(target_arch = "wasm32")]
mod web {
    use solidcraft_engine::io::vfs;
    use wasm_bindgen::JsValue;

    use super::*;

    fn field(params: &JsValue, key: &str) -> Result<String, String> {
        if params.is_undefined() || params.is_null() {
            return Err(format!("missing `{key}`"));
        }
        js_sys::Reflect::get(params, &key.into()).ok().and_then(|v| v.as_string()).ok_or_else(|| format!("`{key}` must be a string"))
    }

    fn reply(pairs: &[(&str, JsValue)]) -> JsValue {
        let object = js_sys::Object::new();
        for (key, value) in pairs {
            let _ = js_sys::Reflect::set(&object, &(*key).into(), value);
        }
        object.into()
    }

    /// `host.write_file {path, base64}` → `{path, bytes}`.
    pub fn write_file(params: &JsValue) -> Result<JsValue, String> {
        let path = field(params, "path")?;
        check_path(&path)?;
        let bytes = decode(&field(params, "base64")?)?;
        let len = bytes.len();
        vfs::insert(&path, bytes);
        Ok(reply(&[("path", path.as_str().into()), ("bytes", (len as f64).into())]))
    }

    /// `host.read_file {path}` → `{path, bytes, base64}`.
    pub fn read_file(params: &JsValue) -> Result<JsValue, String> {
        let path = field(params, "path")?;
        check_path(&path)?;
        let bytes = vfs::read(&path, MAX_BYTES).map_err(|e| e.to_string())?;
        Ok(reply(&[("path", path.as_str().into()), ("bytes", (bytes.len() as f64).into()), ("base64", encode(&bytes).into())]))
    }
}

#[cfg(target_arch = "wasm32")]
pub use web::{read_file, write_file};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn only_plain_names_under_host_are_accepted() {
        for ok in ["/host/part.step", "/host/out.step", "/host/a b (2).dxf", "/host/.hidden", "/host/ünï.stl"] {
            assert_eq!(check_path(ok), Ok(ok), "{ok}");
        }
        let long = format!("/host/{}", "a".repeat(MAX_NAME_CHARS));
        assert!(check_path(&long).is_ok());
        let too_long = format!("/host/{}", "a".repeat(MAX_NAME_CHARS + 1));
        for bad in [
            "/host/../x",
            "/host/..",
            "/host/.",
            "/host/a..b",
            "/etc/x",
            "/hostx",
            "host/x",
            "/host/",
            "/host/a/b",
            "/host/a\\b",
            "/host/a\nb",
            "/host/a\0b",
            "/opfs/x",
            too_long.as_str(),
        ] {
            assert!(check_path(bad).is_err(), "{bad:?}");
        }
    }

    #[test]
    fn base64_round_trips_and_is_bounded() {
        let bytes: Vec<u8> = (0..=255).collect();
        assert_eq!(decode(&encode(&bytes)), Ok(bytes));
        assert_eq!(decode(""), Ok(vec![]));
        assert_eq!(decode("SVNPLTEwMzAzLTIx\n"), Ok(b"ISO-10303-21".to_vec()));
        assert!(decode("not base64!").is_err());
        let over = "A".repeat((MAX_BYTES + 3) / 3 * 4 + 4);
        assert!(matches!(decode(&over), Err(e) if e.contains("64 MiB")));
    }
}
