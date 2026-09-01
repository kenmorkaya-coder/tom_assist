use crate::error::{BrokerError, Result};
use crate::model::CredentialRecord;
#[cfg(test)]
use std::sync::Mutex;

pub(crate) trait CredentialStore: Send + Sync + 'static {
    fn load(&self) -> Result<Option<CredentialRecord>>;
    fn save(&self, record: &CredentialRecord) -> Result<()>;
    fn clear(&self) -> Result<()>;
}

pub struct KeychainStore {
    service: String,
    account: String,
}

impl Default for KeychainStore {
    fn default() -> Self {
        Self {
            service: "local.tom.assist.oauth".into(),
            account: "primary".into(),
        }
    }
}

impl KeychainStore {
    pub fn new(service: impl Into<String>, account: impl Into<String>) -> Self {
        Self {
            service: service.into(),
            account: account.into(),
        }
    }

    fn entry(&self) -> Result<keyring::v1::Entry> {
        keyring::v1::Entry::new(&self.service, &self.account)
            .map_err(|_| BrokerError::new("OAUTH_KEYCHAIN_UNAVAILABLE"))
    }
}

impl CredentialStore for KeychainStore {
    fn load(&self) -> Result<Option<CredentialRecord>> {
        let entry = self.entry()?;
        let secret = match entry.get_secret() {
            Ok(value) => value,
            Err(keyring::v1::Error::NoEntry) => return Ok(None),
            Err(_) => return Err(BrokerError::new("OAUTH_KEYCHAIN_READ_FAILED")),
        };
        let record: CredentialRecord = serde_json::from_slice(&secret)
            .map_err(|_| BrokerError::new("OAUTH_KEYCHAIN_RECORD_INVALID"))?;
        if !record.valid_shape() {
            return Err(BrokerError::new("OAUTH_KEYCHAIN_RECORD_INVALID"));
        }
        Ok(Some(record))
    }

    fn save(&self, record: &CredentialRecord) -> Result<()> {
        if !record.valid_shape() {
            return Err(BrokerError::new("OAUTH_CREDENTIAL_INVALID"));
        }
        let encoded =
            serde_json::to_vec(record).map_err(|_| BrokerError::new("OAUTH_CREDENTIAL_INVALID"))?;
        self.entry()?
            .set_secret(&encoded)
            .map_err(|_| BrokerError::new("OAUTH_KEYCHAIN_WRITE_FAILED"))
    }

    fn clear(&self) -> Result<()> {
        let entry = self.entry()?;
        match entry.delete_credential() {
            Ok(()) | Err(keyring::v1::Error::NoEntry) => Ok(()),
            Err(_) => Err(BrokerError::new("OAUTH_KEYCHAIN_DELETE_FAILED")),
        }
    }
}

#[cfg(test)]
#[derive(Default)]
pub(crate) struct MemoryStore {
    record: Mutex<Option<CredentialRecord>>,
}

#[cfg(test)]
impl CredentialStore for MemoryStore {
    fn load(&self) -> Result<Option<CredentialRecord>> {
        Ok(self.record.lock().expect("memory store poisoned").clone())
    }

    fn save(&self, record: &CredentialRecord) -> Result<()> {
        *self.record.lock().expect("memory store poisoned") = Some(record.clone());
        Ok(())
    }

    fn clear(&self) -> Result<()> {
        *self.record.lock().expect("memory store poisoned") = None;
        Ok(())
    }
}
