//! One archive/backup implementation used by desktop and integration tests.
use std::path::{Path, PathBuf};
use tom_assist_persistence::{Project, Store, StoreError};
use tom_assist_tom_adapter::GatewayClient;

pub fn verify_project(
    gateway: &GatewayClient,
    directory: &Path,
) -> crate::Result<serde_json::Value> {
    let verified = Store::verify_recovery_archive(directory)?;
    let runtime = gateway
        .verify_runtime(&directory.join("runtime"))
        .map_err(|error| StoreError::Integrity(error.to_string()))?;
    if runtime != verified["runtime"] {
        return Err(
            StoreError::Integrity("runtime manifest changed during verification".into()).into(),
        );
    }
    Ok(verified)
}

pub fn export_project(
    store: &Store,
    gateway: &GatewayClient,
    project_id: &str,
    directory: &Path,
) -> crate::Result<PathBuf> {
    Ok(
        store.export_recovery_archive(project_id, directory, |runtime_dir| {
            gateway
                .export_runtime(project_id, runtime_dir)
                .map_err(|e| StoreError::Integrity(e.to_string()))
        })?,
    )
}
pub fn import_project(
    store: &mut Store,
    gateway: &GatewayClient,
    directory: &Path,
) -> crate::Result<Project> {
    Ok(
        store.import_recovery_archive(directory, |action, runtime_dir, context| {
            gateway
                .import_runtime(action, runtime_dir, context)
                .map_err(|e| StoreError::Integrity(e.to_string()))
        })?,
    )
}
