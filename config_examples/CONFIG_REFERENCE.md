# Configuration Files Reference

**Version:** v0.4.0  
**Date:** December 26, 2024

Documentazione completa di tutti i file di configurazione JSON e i loro campi.

---

## Indice

1. [common.json](#commonjson) - Configurazione globale condivisa
2. [sync.json](#syncjson) - Sincronizzazione one-way
3. [compare.json](#comparejson) - Comparazione cartelle
4. [bisync.json](#bisyncjson) - Sincronizzazione bidirezionale
5. [backup.json](#backupjson) - Backup semplice con zip
6. [backup_extended.json](#backup_extendedjson) - Backup multi-archive avanzato
7. [FilterConfig](#filterconfig) - Opzioni di filtraggio (riutilizzabile)
8. [FolderPair](#folderpair) - Coppia cartelle con override (sync/compare/bisync)

---

## common.json

**Scopo:** Configurazione globale condivisa da tutte le operazioni rclone.

### Campi Obbligatori

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `remote` | string | Nome del remote rclone configurato (es. "gdrive", "agdrive") |

### Campi Opzionali

| Campo | Tipo | Default | Descrizione |
|-------|------|---------|-------------|
| `log_dir` | string | `"logs"` | Directory per i file di log |
| `log_level` | string | `"INFO"` | Livello di logging: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"` |
| `bwlimit` | string | `null` | Limite banda (es. `"8M"`, `"1G"`, `"500k"`) |
| `transfers` | integer | `4` | Numero trasferimenti paralleli (1-32) |
| `checkers` | integer | `8` | Numero checker paralleli (1-32) |
| `timeout` | integer | `7200` | Timeout operazioni in secondi (min 60) |
| `dry_run` | boolean | `false` | Se `true`, simula operazioni senza eseguirle |
| `extra_flags` | array | `[]` | Flag rclone aggiuntivi custom |
| `filters` | FilterConfig | `{}` | Filtri globali applicati a tutte le operazioni |

### Esempio

```json
{
  "remote": "agdrive",
  "log_dir": "logs",
  "log_level": "INFO",
  "bwlimit": "8M",
  "transfers": 4,
  "checkers": 8,
  "timeout": 7200,
  "dry_run": false,
  "extra_flags": [],
  "filters": {
    "exclude": [
      "*.tmp",
      "*.bak",
      ".DS_Store",
      "Thumbs.db"
    ],
    "exclude_dirs": [
      ".git",
      "node_modules",
      "__pycache__"
    ]
  }
}
```

### Note

- **remote**: Deve corrispondere a un remote configurato in rclone (`rclone config`)
- **bwlimit**: Suffisso `k`/`K` (KB/s), `m`/`M` (MB/s), `g`/`G` (GB/s)
- **transfers**: Più alto = più veloce ma più RAM/CPU
- **checkers**: Verifica file esistenti; più alto = più veloce inizializzazione
- **filters**: Questi filtri sono **sempre applicati** e poi mergiati con filtri operation-specific

---

## sync.json

**Scopo:** Configurazione per sincronizzazioni one-way (local → remote o remote → local).

### Campi Obbligatori

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `remote` | string | Nome del remote configurato in rclone (es. `"agdrive"`). Usato per validazione |
| `folders` | array\<FolderPair\> | Lista di coppie cartelle da sincronizzare |

### Campi Opzionali Globali

| Campo | Tipo | Default | Descrizione |
|-------|------|---------|-------------|
| `checksum` | boolean | `false` | Usa checksum per comparazione (più lento ma accurato) |
| `size_only` | boolean | `false` | Compara solo dimensione file (ignora modtime) |
| `modtime_and_size` | boolean | `true` | Compara dimensione + data modifica (default rclone) |
| `filters` | FilterConfig | `{}` | Filtri globali per questa operation (mergiati con common) |

### FolderPair Override

Ogni elemento in `folders` può sovrascrivere:
- `filters` (REPLACE - ignora completamente filtri globali)
- `checksum`
- `size_only`

### Esempi

#### Minimalista (NUOVO FORMATO)
```json
{
  "remote": "agdrive",
  "checksum": true,
  "filters": {
    "exclude": ["~*", "*.swp"]
  },
  "folders": [
    {
      "source": "\\\\nas\\data",
      "destination": "agdrive:backup/data"
    },
    {
      "source": "C:\\Users\\john\\Documents",
      "destination": "agdrive:backup/documents"
    }
  ]
}
```

**⚠️ IMPORTANTE:** Destinazioni sempre con formato esplicito `remote:path`

#### Con Override Per-Coppia
```json
{
  "remote": "agdrive",
  "checksum": true,
  "size_only": false,
  "filters": {
    "exclude": ["~*", "*.swp"]
  },
  "folders": [
    {
      "source": "\\\\nas\\projects",
      "destination": "agdrive:backup/projects",
      "filters": {
        "exclude": ["node_modules/**", "dist/**", "*.log"]
      }
    },
    {
      "source": "\\\\nas\\photos",
      "destination": "agdrive:backup/photos",
      "size_only": true,
      "checksum": false
    }
  ]
}
```

### Note

- **Path Espliciti**: Tutte le destinazioni devono essere path completi: `"agdrive:atlas/subfolder"`
- **Validazione**: Il sistema valida che il remote nella destinazione corrisponda al campo `remote`
- **Auto-detect**: `is_remote_path()` rileva se path contiene `:` (esclude drive Windows `C:`, `D:`)
- **Direzione**: source/destination possono essere local o remote (rilevato automaticamente)
- **Normalizzazione**: I path sono automaticamente normalizzati (backslash → forward slash)
- **Upload**: source locale + destination remote; **Download**: source remote + destination locale
- **checksum vs size_only**: Mutualmente esclusivi; checksum = hash SHA1, size_only = solo dimensione
- **Override filters**: Se specificato, **SOSTITUISCE completamente** filtri globali (non merge)

---

## compare.json

**Scopo:** Confronta cartelle per verificare sincronizzazione senza modificare file.

### Campi Obbligatori

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `remote` | string | Nome del remote configurato in rclone (es. `"agdrive"`). Usato per validazione |
| `folders` | array\<FolderPair\> | Lista di coppie cartelle da comparare |

### Campi Opzionali Globali

| Campo | Tipo | Default | Descrizione |
|-------|------|---------|-------------|
| `one_way` | boolean | `true` | `true` = verifica solo source→dest; `false` = bidirezionale |
| `download` | boolean | `false` | `true` = scarica file remoti per confronto (più lento ma accurato) |
| `checksum` | boolean | `false` | Usa checksum per comparazione |
| `size_only` | boolean | `false` | Compara solo dimensione |
| `filters` | FilterConfig | `{}` | Filtri globali (mergiati con common) |

### FolderPair Override

Ogni elemento in `folders` può sovrascrivere:
- `filters` (REPLACE)
- `one_way`
- `download`
- `checksum`
- `size_only`

### Esempi

#### Comparazione Semplice
```json
{
  "remote": "agdrive",
  "one_way": false,
  "checksum": true,
  "filters": {
    "exclude": ["~*", "*.tmp"]
  },
  "folders": [
    {
      "source": "\\\\nas\\data",
      "destination": "agdrive:backup/data"
    }
  ]
}
```

#### Con Override Selettivo
```json
{
  "remote": "agdrive",
  "one_way": false,
  "download": false,
  "checksum": true,
  "folders": [
    {
      "source": "\\\\nas\\critical_data",
      "destination": "agdrive:backup/critical_data",
      "one_way": true,
      "download": true
    },
    {
      "source": "\\\\nas\\logs",
      "destination": "agdrive:backup/logs",
      "checksum": false,
      "size_only": true
    }
  ]
}
```

### Note

- **Path Espliciti**: Tutte le destinazioni devono usare formato `remote:path` completo
- **Validazione**: Il remote viene validato contro il campo `remote` configurato
- **one_way=true**: Ignora file extra in destination (solo source→dest), ovvero controlla esclusivamente i file presenti nella cartella sorgente.
- **one_way=false**: Bidirezionale, segnala file mancanti in entrambe le direzioni
- **download=true**: Scarica file remoti per checksum locale (più accurato ma lento e usa banda)

---

## bisync.json

**Scopo:** Sincronizzazione bidirezionale (two-way sync) tra due directory.

### Campi Obbligatori

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `remote` | string | Nome del remote configurato in rclone (es. `"agdrive"`). Usato per validazione |
| `folders` | array\<FolderPair\> | Lista di coppie cartelle per bisync |

### Campi Opzionali Globali

| Campo | Tipo | Default | Descrizione |
|-------|------|---------|-------------|
| `state_dir` | string | `"bisync_state"` | Directory stato bisync (tracking) |
| `backup_dir` | string | `"bisync_backups"` | Directory backup file conflitti |
| `checksum` | boolean | `false` | Usa checksum per comparazione |
| `filters` | FilterConfig | `{}` | Filtri globali (mergiati con common) |

### Opzioni Bisync Specifiche

| Campo | Tipo | Default | Descrizione |
|-------|------|---------|-------------|
| `resilient` | boolean | `true` | Continua anche con errori non-critici |
| `recover` | boolean | `true` | Tenta recovery da interruzioni precedenti |
| `force` | boolean | `false` | ⚠️ Forza sync anche con molte modifiche (usa con cautela) |
| `max_lock` | string | `"2m"` | Timeout lock file (es. `"30s"`, `"5m"`, `"1h"`) |
| `conflict_resolve` | string | `"none"` | Strategia risoluzione conflitti: `"none"`, `"newer"`, `"older"`, `"larger"`, `"smaller"` |
| `conflict_loser` | string | `"num"` | Gestione file perdente: `"num"` (numerato), `"pathname"`, `"delete"` |
| `conflict_suffix` | string | `"conflict"` | Suffisso per file conflitti (es. `file.conflict.txt`) |
| `resync_mode` | string | `"none"` | Modalità resync: `"none"`, `"path1"`, `"path2"` |
| `compare` | array | `["size", "modtime"]` | Metodi comparazione: `"size"`, `"modtime"`, `"checksum"` |
| `create_empty_src_dirs` | boolean | `true` | Crea directory vuote in destinazione |

### FolderPair Override

Ogni elemento in `folders` può sovrascrivere:
- `filters` (REPLACE)
- `checksum`

### Esempio

```json
{
  "remote": "agdrive",
  "state_dir": "bisync_state",
  "backup_dir": "bisync_backups",
  "resilient": true,
  "recover": true,
  "force": false,
  "max_lock": "2m",
  "conflict_resolve": "none",
  "conflict_loser": "num",
  "conflict_suffix": "conflict",
  "resync_mode": "none",
  "compare": ["size", "modtime"],
  "create_empty_src_dirs": true,
  "checksum": false,
  "filters": {
    "exclude": ["~*", "*.swp", "*.log"],
    "exclude_dirs": [".vscode", ".idea"]
  },
  "folders": [
    {
      "source": "\\\\nas\\docs",
      "destination": "agdrive:atlas/docs"
    },
    {
      "source": "\\\\nas\\projects",
      "destination": "agdrive:atlas/projects",
      "filters": {
        "exclude": ["node_modules/**", "*.pdf"]
      },
      "checksum": true
    }
  ]
}
```

### Note

- **Path Espliciti**: Tutte le destinazioni devono usare formato `remote:path` completo
- **Validazione**: Il remote viene validato contro il campo `remote` configurato
- **Prima esecuzione**: Richiede `--resync` per inizializzazione
- **force=true**: ⚠️ Pericoloso - bypassa safety checks per cambiamenti massivi
- **conflict_resolve="none"**: Crea copie di conflitto invece di scegliere automaticamente
- **max_lock**: Previene lock infiniti; regola in base a durata operazione
- **state_dir**: Contiene `.lst` files per tracking cambiamenti

---

## backup.json

**Scopo:** Backup semplice con creazione ZIP e gestione retention.

### Campi Obbligatori

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `dest_base` | string | Path di destinazione per gli archivi ZIP |
| `folders` | array\<string\> | Lista di cartelle da backuppare |

### Campi Opzionali

| Campo | Tipo | Default | Descrizione |
|-------|------|---------|-------------|
| `zip_prefix` | string | `"backup"` | Prefisso per nome file ZIP (es. `backup_20241226.zip`) |
| `retention_days` | integer | `30` | Giorni di retention (1-365) |

### Esempio

```json
{
  "dest_base": "backuptest/archives",
  "zip_prefix": "backup",
  "retention_days": 30,
  "folders": [
    "C:\\Users\\john\\Documents",
    "C:\\Users\\john\\Pictures",
    "\\\\nas\\important_data"
  ]
}
```

### Note

- **ZIP naming**: `{zip_prefix}_{YYYYMMDD_HHMMSS}.zip`
- **Retention**: Elimina ZIP più vecchi di `retention_days`
- **Filters**: Usa solo filtri da `common.json` (non ha filtri propri)

---

## backup_extended.json

**Scopo:** Backup multi-archive con gestione avanzata, filtri per-archive, merge opzionale.

### Campi Obbligatori

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `dest_base` | string | Path di destinazione per gli archivi |
| `archives` | array\<ArchiveConfig\> | Lista di configurazioni archive |

### Campi Opzionali

| Campo | Tipo | Default | Descrizione |
|-------|------|---------|-------------|
| `filters` | FilterConfig | `{}` | Filtri globali per tutti gli archive |
| `max_retention_days` | integer | `30` | Retention massima consentita (1-365) |

### ArchiveConfig

Ogni elemento in `archives`:

| Campo | Tipo | Default | Descrizione |
|-------|------|---------|-------------|
| `source` | array\<string\> | **required** | Lista di cartelle sorgente |
| `destination` | string | **required** | Nome cartella destinazione (e prefisso ZIP) |
| `filters` | FilterConfig | `null` | Filtri specifici (sostituisce globali se specificato) |
| `retention_days` | integer | `30` | Giorni retention per questo archive |
| `merge_zip` | boolean | `true` | `true`=singolo ZIP; `false`=ZIP separato per ogni source |
| `compression_level` | integer | `6` | Livello compressione ZIP (0-9): 0=nessuna, 9=massima |
| `enabled` | boolean | `true` | Abilita/disabilita questo archive |
| `description` | string | `null` | Descrizione opzionale |

### Esempio

```json
{
  "dest_base": "backuptest/archives",
  "max_retention_days": 30,
  "filters": {
    "exclude": ["*.tmp", "*.bak", "~*"],
    "exclude_dirs": [".git", "node_modules"]
  },
  "archives": [
    {
      "source": [
        "C:\\Users\\john\\Documents",
        "C:\\Users\\john\\Desktop"
      ],
      "destination": "documents_archive",
      "filters": {
        "exclude": ["*.log"]
      },
      "retention_days": 15,
      "merge_zip": true,
      "compression_level": 6,
      "enabled": true,
      "description": "Documents backup - merged into single archive"
    },
    {
      "source": [
        "C:\\Users\\john\\Pictures",
        "C:\\Users\\john\\Videos"
      ],
      "destination": "media_archive",
      "filters": null,
      "retention_days": 7,
      "merge_zip": false,
      "compression_level": 9,
      "enabled": true,
      "description": "Media files - separate archives"
    }
  ]
}
```

### Note

- **merge_zip=true**: Crea `destination_YYYYMMDD_HHMMSS.zip` con tutte le source
- **merge_zip=false**: Crea ZIP separato per ogni source folder
- **compression_level**: 0=store (veloce), 6=bilanciato, 9=massimo (lento)
- **filters=null**: Usa filtri globali; se specificato, SOSTITUISCE (non merge)
- **enabled=false**: Archive viene saltato durante backup

---

## FilterConfig

**Scopo:** Configurazione riutilizzabile per filtraggio file/directory.

### Campi (Tutti Opzionali)

| Campo | Tipo | Default | Descrizione |
|-------|------|---------|-------------|
| `exclude` | array\<string\> | `[]` | Pattern glob da escludere (es. `"*.tmp"`, `"node_modules/**"`) |
| `include` | array\<string\> | `[]` | Pattern glob da includere (ha precedenza su exclude) |
| `exclude_dirs` | array\<string\> | `[]` | Nomi directory da escludere (es. `".git"`, `"__pycache__"`) |
| `exclude_if_present` | string | `null` | Escludi directory se contiene questo file (es. `".nomedia"`) |
| `min_size` | string | `null` | Dimensione minima file (es. `"100k"`, `"10M"`, `"1G"`) |
| `max_size` | string | `null` | Dimensione massima file (es. `"100M"`, `"5G"`) |
| `min_age` | string | `null` | Età minima file (es. `"7d"`, `"2w"`, `"1m"`) |
| `max_age` | string | `null` | Età massima file (es. `"30d"`, `"6m"`, `"1y"`) |
| `filter_from` | string | `null` | Leggi filtri da file (path al file) |
| `ignore_case` | boolean | `false` | Ignora maiuscole/minuscole nei pattern |

### Sintassi Pattern

- **Glob**: `*.txt`, `**/*.log` (ricorsivo), `dir/**/file.dat`
- **Exclude directory**: Solo nome (es. `"node_modules"`, non `"node_modules/"`)
- **Size**: Suffisso `k`/`K`, `m`/`M`, `g`/`G`, `t`/`T`
- **Age**: Suffisso `s` (secondi), `m` (minuti), `h` (ore), `d` (giorni), `w` (settimane), `M` (mesi), `y` (anni)

### Esempio

```json
{
  "filters": {
    "exclude": [
      "*.tmp",
      "*.bak",
      "~*",
      "Thumbs.db",
      ".DS_Store",
      "desktop.ini",
      "node_modules/**",
      "dist/**",
      ".cache/**"
    ],
    "include": [
      "important_*.tmp"
    ],
    "exclude_dirs": [
      ".git",
      ".svn",
      "__pycache__",
      ".venv",
      "venv",
      ".idea",
      ".vscode"
    ],
    "exclude_if_present": ".nomedia",
    "min_size": "100k",
    "max_size": "5G",
    "min_age": "7d",
    "max_age": "365d",
    "filter_from": null,
    "ignore_case": false
  }
}
```

### Ordine di Valutazione

1. **include** (se match, file incluso)
2. **exclude** (se match, file escluso)
3. **exclude_dirs** (se directory name match, esclusa)
4. **exclude_if_present** (se file presente, directory esclusa)
5. **min_size/max_size** (verifica dimensione)
6. **min_age/max_age** (verifica età)

---

## FolderPair

**Scopo:** Coppia di cartelle con override opzionali (usato in sync/compare/bisync).

### Campi Obbligatori

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `source` | string | Path sorgente (locale o `remote:path`) |
| `destination` | string | Path destinazione esplicito con formato `remote:path` (es. `"agdrive:atlas/folder"`) |

### Campi Opzionali (Override)

| Campo | Tipo | Default | Disponibile In | Descrizione |
|-------|------|---------|----------------|-------------|
| `filters` | FilterConfig | `null` | sync, compare, bisync | Override filtri (REPLACE globali) |
| `checksum` | boolean | `null` | sync, compare, bisync | Override comparazione checksum |
| `size_only` | boolean | `null` | sync, compare | Override comparazione solo size |
| `one_way` | boolean | `null` | compare | Override modalità one-way |
| `download` | boolean | `null` | compare | Override download per comparazione |

### Comportamento Override

- **`null`/non specificato**: Usa valore globale da config operation
- **Valore specificato**: SOSTITUISCE valore globale per questa coppia
- **`filters` specificato**: SOSTITUISCE completamente filtri globali (non merge)

### Esempi

#### Path Esplicito (FORMATO OBBLIGATORIO)
```json
{
  "source": "\\\\nas\\data",
  "destination": "agdrive:backup/data"
}
```

**⚠️ IMPORTANTE:** Destinazione sempre con formato esplicito `remote:path`

#### Con Override Filters
```json
{
  "source": "\\\\nas\\projects",
  "destination": "agdrive:atlas/projects",
  "filters": {
    "exclude": ["node_modules/**", "dist/**", "*.log"]
  }
}
```

#### Con Override Multipli
```json
{
  "source": "\\\\nas\\photos",
  "destination": "photos",
  "checksum": false,
  "size_only": true,
  "filters": {
    "exclude": ["*.tmp"],
    "min_size": "10k",
    "max_size": "100M"
  }
}
```

### Note

- **Auto-detect path**: `is_remote_path()` rileva formato `remote:path` (esclude drive Windows `C:`, `D:`)
- **Path espliciti**: OBBLIGATORIO usare formato completo `remote:path` per tutte le destinazioni
- **Validazione fail-fast**: Errori di configurazione vengono rilevati all'avvio, non durante l'esecuzione
- **REPLACE behavior**: Override `filters` ignora completamente filtri globali (non merge)
- **Priority chain**: `pair.override → operation.global → common.global → default`

---

## Best Practices

### 1. Struttura Path (NUOVO FORMATO)

**✅ Usa sempre path espliciti:**
```json
{
  "remote": "agdrive",
  "folders": [
    {"source": "\\\\nas\\docs", "destination": "agdrive:atlas/docs"},
    {"source": "\\\\nas\\photos", "destination": "agdrive:atlas/photos"}
  ]
}
```

**Vantaggi del nuovo formato:**
- ✅ Zero ambiguità: path sempre completi ed espliciti
- ✅ Validazione automatica: fail-fast se remote non corrisponde
- ✅ Normalizzazione: backslash → forward slash automatico
- ✅ Type-safe: Pydantic valida la struttura JSON
- ✅ Principio "Explicit is better than implicit" (PEP 20)

**❌ Non più supportato (formato legacy):**
```json
// OBSOLETO - non funziona più
{"dest_base": "atlas", "destination": "docs"}
```

### 2. Organizzazione Filtri

**common.json** - Filtri universali:
```json
"filters": {
  "exclude": ["*.tmp", "*.bak", ".DS_Store", "Thumbs.db"],
  "exclude_dirs": [".git", "__pycache__"]
}
```

**operation.json** - Filtri operation-specific:
```json
"filters": {
  "exclude": ["*.log", "*.cache"]
}
```

**FolderPair** - Filtri per coppia eccezionale:
```json
{
  "source": "...",
  "destination": "...",
  "filters": {
    "exclude": ["node_modules/**", "dist/**"]
  }
}
```

### 2. Performance Tuning

**Trasferimenti Veloci (SSD, banda alta):**
```json
{
  "transfers": 8,
  "checkers": 16,
  "bwlimit": null
}
```

**Trasferimenti Lenti (HDD, banda limitata):**
```json
{
  "transfers": 2,
  "checkers": 4,
  "bwlimit": "2M"
}
```

### 3. Comparazione File

**Veloce (solo metadata):**
```json
{
  "checksum": false,
  "size_only": false,
  "modtime_and_size": true
}
```

**Accurato (hash):**
```json
{
  "checksum": true,
  "size_only": false
}
```

**Foto/Video (solo size):**
```json
{
  "checksum": false,
  "size_only": true
}
```

### 4. Override Selettivo

90% delle coppie devono usare solo `{source, destination}`.  
Override solo quando **realmente diverso** da globale:

❌ **Non fare:**
```json
{
  "source": "...",
  "destination": "...",
  "checksum": true,  // Uguale a globale!
  "filters": {       // Uguale a globale!
    "exclude": ["*.tmp"]
  }
}
```

✅ **Fare:**
```json
{
  "checksum": true,  // Globale
  "filters": {
    "exclude": ["*.tmp"]
  },
  "folders": [
    {
      "source": "...",
      "destination": "..."
    },
    {
      "source": "...",
      "destination": "...",
      "checksum": false  // Solo qui diverso
    }
  ]
}
```

### 5. Dry Run Testing

Prima di operazioni importanti:
```json
{
  "dry_run": true
}
```

Verifica log, poi esegui:
```json
{
  "dry_run": false
}
```

---

## Troubleshooting

### Errore: "Invalid bwlimit format"
**Soluzione:** Usa suffisso corretto: `"8M"`, `"500k"`, `"1G"` (non `"8MB"` o `"8Mbps"`)

### Errore: "At least one source folder must be specified"
**Soluzione:** `backup_extended.json` - ogni archive deve avere almeno 1 source

### Filtri non applicati
**Problema:** Override filters sostituisce completamente globali  
**Soluzione:** Se vuoi merge, non usare override - lascia filters solo in global

### Bisync non sincronizza
**Problema:** Prima esecuzione richiede `--resync`  
**Soluzione:** Esegui `rclone bisync --resync path1 path2` manualmente

### Timeout su file grandi
**Soluzione:** Aumenta `timeout` in common.json (es. `14400` per 4 ore)

---

## Validazione

Tutti i config sono validati con Pydantic. Errori comuni:

- **Type mismatch**: `"transfers": "4"` → deve essere integer: `"transfers": 4`
- **Out of range**: `"transfers": 100` → massimo 32
- **Invalid enum**: `"log_level": "TRACE"` → valori: DEBUG, INFO, WARNING, ERROR
- **Missing required**: `sync.json` senza `dest_base`

Esegui test:
```python
from rclone_wrapper.config import load_sync_config, load_common_config

common = load_common_config()
sync = load_sync_config()
print("✅ Config valid!")
```

---

## Changelog

**v0.4.0 (2024-12-26)**
- Aggiunto `FolderPair` model con override per sync/compare/bisync
- Filtri globali + per-operation + per-pair
- Override behavior: REPLACE (non merge)
- Breaking change: `folders` ora `List[FolderPair]` invece di `List[Dict]`

**v0.3.0 (2024-12-25)**
- Unified logging system
- Bug fix: JSON logs parsing (stdout vs stderr)

---

## Riferimenti

- **Pydantic Models**: `rclone_wrapper/config.py`
- **Migration Guide**: `MIGRATION_UNIFIED_CONFIG.md`
- **Rclone Docs**: https://rclone.org/docs/
