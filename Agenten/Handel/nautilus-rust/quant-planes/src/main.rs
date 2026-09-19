use serde::Deserialize;
use std::collections::{HashMap, HashSet};
use std::path::Path;

#[derive(Deserialize)]
struct LockPackage {
    name: String,
    #[serde(default)]
    dependencies: Vec<String>,
}

#[derive(Deserialize)]
struct LockFile {
    package: Vec<LockPackage>,
}

/// Baut die transitive Abhaengigkeitsmenge einer Crate aus Cargo.lock.
fn transitive_deps(lock: &LockFile, root: &str) -> HashSet<String> {
    let mut by_name: HashMap<&str, &LockPackage> = HashMap::new();
    for p in &lock.package {
        by_name.insert(p.name.as_str(), p);
    }
    let mut seen = HashSet::new();
    let mut stack = vec![root.to_string()];
    while let Some(name) = stack.pop() {
        if !seen.insert(name.clone()) {
            continue;
        }
        if let Some(p) = by_name.get(name.as_str()) {
            for d in &p.dependencies {
                stack.push(d.clone());
            }
        }
    }
    seen
}

#[cfg(test)]
fn alpha_deps() -> HashSet<String> {
    let lock = read_lock();
    transitive_deps(&lock, "quant-alpha")
}

#[cfg(test)]
fn strategy_deps() -> HashSet<String> {
    let lock = read_lock();
    transitive_deps(&lock, "quant-strategy")
}

fn read_lock() -> LockFile {
    // CARGO_MANIFEST_DIR zeigt auf das Crate-Verzeichnis; Cargo.lock liegt
    // eine Ebene hoeher im Workspace-Root.
    let lock_path = Path::new(env!("CARGO_MANIFEST_DIR")).join("../Cargo.lock");
    let raw = std::fs::read_to_string(&lock_path).expect("Cargo.lock lesen");
    toml::from_str(&raw).expect("Cargo.lock parsen")
}

fn main() {
    let lock = read_lock();
    let alpha = transitive_deps(&lock, "quant-alpha");
    let strategy = transitive_deps(&lock, "quant-strategy");

    let mut violations = Vec::new();
    for d in &alpha {
        if d.starts_with("nautilus-") {
            violations.push(format!("quant-alpha -> {}", d));
        }
    }
    for d in &strategy {
        if d.starts_with("candle-") {
            violations.push(format!("quant-strategy -> {}", d));
        }
    }

    if violations.is_empty() {
        println!("quant-planes: 0 violations (Ebenen-Grenze sauber)");
        std::process::exit(0);
    } else {
        for v in &violations {
            eprintln!("quant-planes: VERSTOSS {}", v);
        }
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn alpha_plane_has_no_nautilus() {
        let deps = alpha_deps();
        assert!(
            !deps.iter().any(|d| d.starts_with("nautilus-")),
            "quant-alpha darf kein nautilus-*-Crate haben, hatte: {:?}",
            deps.iter()
                .filter(|d| d.starts_with("nautilus-"))
                .collect::<Vec<_>>()
        );
    }

    #[test]
    fn strategy_plane_has_no_candle() {
        let deps = strategy_deps();
        assert!(
            !deps.iter().any(|d| d.starts_with("candle-")),
            "quant-strategy darf kein candle-*-Crate haben, hatte: {:?}",
            deps.iter()
                .filter(|d| d.starts_with("candle-"))
                .collect::<Vec<_>>()
        );
    }
}
