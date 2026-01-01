"""
Adapters per convertire output rclone in stream di FileOperation.

Questo modulo fornisce adattatori che trasformano l'output di rclone
(text format o NDJSON) in stream di FileOperation che possono essere processati
da StreamLogProcessor.

Design: Adapter Pattern - converte interfaccia rclone → interfaccia domain.
"""

import json
from datetime import datetime
from typing import Iterator, Optional

from ..domain import FileOperation, FileState


class RcloneOutputAdapter:
    """
    Adapter per convertire output rclone NDJSON in stream di FileOperation.
    
    Responsabilità:
    1. Parse NDJSON da rclone
    2. Mappa log entries → FileOperation objects
    3. Produce stream Iterator[FileOperation]
    
    Design Note:
    - Stateless (può essere usato per più conversioni)
    - Lazy evaluation (generator/iterator)
    - Error resilient (skip malformed lines)
    
    Example:
        >>> adapter = RcloneOutputAdapter()
        >>> rclone_output = '''
        ... {"level":"info","msg":"Copied","object":"file.txt","size":1024}
        ... {"level":"info","msg":"Deleted","object":"old.txt"}
        ... '''
        >>> operations = adapter.parse_stream(rclone_output)
        >>> for op in operations:
        ...     print(op.path, op.action)
        file.txt copy
        old.txt delete
    """
    
    @staticmethod
    def parse_stream(
        rclone_output: str,
        operation_type: Optional[str] = None
    ) -> Iterator[FileOperation]:
        """
        Parse rclone text output e produce stream di FileOperation.
        
        IMPORTANTE: rclone NON emette JSON di default, ma testo formattato!
        Esempio output:
            2025/12/28 19:46:52 INFO  : - Path1    File is new      - TEST1.docx
            2025/12/28 19:46:53 INFO  : TEST1.docx: Copied (new)
        
        Args:
            rclone_output: Raw text output da rclone (stderr)
            operation_type: Tipo di operazione (sync, bisync, compare) - opzionale
        
        Yields:
            FileOperation objects estratti dall'output
        
        Note:
            - Parse text format, non JSON
            - Cerca pattern come "Copied (new)", "Deleted", etc.
        """
        for line in rclone_output.splitlines():
            line = line.strip()
            if not line:
                continue
            
            try:
                # Prova prima JSON (se --use-json-log era abilitato)
                entry = json.loads(line)
                operation = RcloneOutputAdapter._parse_log_entry(
                    entry, 
                    operation_type
                )
                if operation:
                    yield operation
                    
            except json.JSONDecodeError:
                # Non è JSON, prova text parsing
                operation = RcloneOutputAdapter._parse_text_line(
                    line,
                    operation_type
                )
                if operation:
                    yield operation
            except Exception:
                # Skip errori di parsing - resilience
                continue
    
    @staticmethod
    def _parse_text_line(
        line: str,
        operation_type: Optional[str] = None
    ) -> Optional[FileOperation]:
        """
        Parse singola riga di testo da rclone output.
        
        Rclone text format examples:
            2025/12/28 19:46:53 INFO  : TEST1.docx: Copied (new)
            2025/12/28 19:46:52 INFO  : - Path1    File is new               - TEST1.docx
            2025/12/28 19:46:52 INFO  : - Path1    Queue copy to Path2       - agdrive:test/file.txt
            2025/12/28 19:46:53 NOTICE: file.txt: Deleted
        
        Args:
            line: Singola riga di log da rclone
            operation_type: Tipo operazione (per context)
        
        Returns:
            FileOperation se la riga descrive un'operazione su file, None altrimenti
        """
        # Pattern comuni negli output rclone
        # Format: "FILENAME: ACTION"
        if ': ' in line and any(keyword in line for keyword in [
            'Copied (new)', 'Copied (replaced', 'Deleted', 'Moved', 'Renamed'
        ]):
            # Extract filename e action dalla riga
            # Es: "2025/12/28 19:46:53 INFO  : TEST1.docx: Copied (new)"
            parts = line.split(': ', 1)  # Split in 2 parti: timestamp e messaggio
            if len(parts) >= 2:
                message = parts[1].strip()
                
                # Parse "FILENAME: ACTION"
                if ': ' in message:
                    filename, action_text = message.split(': ', 1)
                    action = RcloneOutputAdapter._extract_action_from_text(action_text)
                    
                    if action:
                        return FileOperation(
                            path=filename.strip(),
                            action=action,
                            source=FileState(exists=True),
                            destination=FileState(exists=action != 'delete'),
                            status='success',
                            timestamp=datetime.now().isoformat(),
                        )
        
        # Bisync format: "- Path1    ACTION    - FILENAME"
        if operation_type == 'bisync' and '- Path' in line:
            # Es: "- Path1    File is new               - TEST1.docx"
            # Es: "- Path1    Queue copy to Path2       - agdrive:test/file.txt"
            
            # Cerca pattern "- FILENAME" alla fine
            if line.count(' - ') >= 2:
                # L'ultimo " - " separa il filename
                last_dash_idx = line.rfind(' - ')
                filename = line[last_dash_idx + 3:].strip()
                
                # Il testo prima contiene l'azione
                action_part = line[:last_dash_idx]
                
                # Determina azione dal testo
                if 'File is new' in action_part or 'new' in action_part.lower():
                    action = 'copy'
                elif 'Queue copy' in action_part:
                    action = 'copy'
                elif 'delete' in action_part.lower():
                    action = 'delete'
                elif 'update' in action_part.lower() or 'modified' in action_part.lower():
                    action = 'update'
                else:
                    # Non riconosciuto, skip
                    return None
                
                return FileOperation(
                    path=filename,
                    action=action,
                    source=FileState(exists=True),
                    destination=FileState(exists=action != 'delete'),
                    status='success',
                    timestamp=datetime.now().isoformat(),
                )
        
        return None
    
    @staticmethod
    def _extract_action_from_text(action_text: str) -> Optional[str]:
        """
        Estrai azione da testo descrittivo.
        
        Args:
            action_text: Testo come "Copied (new)", "Deleted", etc.
        
        Returns:
            Action string (copy, delete, update, etc.) o None
        """
        action_text_lower = action_text.lower()
        
        if 'copied (new)' in action_text_lower:
            return 'copy'
        elif 'copied (replaced' in action_text_lower or 'copied (updated' in action_text_lower:
            return 'update'
        elif 'copied' in action_text_lower:
            return 'copy'
        elif 'deleted' in action_text_lower:
            return 'delete'
        elif 'moved' in action_text_lower or 'renamed' in action_text_lower:
            return 'rename'
        elif 'updated' in action_text_lower:
            return 'update'
        
        return None
    
    @staticmethod
    def _parse_log_entry(
        entry: dict,
        operation_type: Optional[str] = None
    ) -> Optional[FileOperation]:
        """
        Parse singolo log entry JSON da rclone --use-json-log.
        
        Args:
            entry: Parsed JSON entry da rclone
            operation_type: Tipo operazione (per context)
        
        Returns:
            FileOperation se entry contiene info su file, altrimenti None
        
        Rclone JSON Log Format Examples:
            {"time":"2025-12-29T12:36:52.465921+01:00","level":"info","msg":"Copied (new)",
             "size":6197,"object":"file.xlsx","objectType":"*local.Object","source":"slog/logger.go:256"}
            {"level":"info","msg":"Deleted","object":"old.txt"}
            {"level":"info","msg":"Set directory modification time","object":"folder","objectType":"*drive.Directory"}
        """
        # Estrai campo "object" - se assente, non è operazione su file
        obj = entry.get("object")
        if not obj:
            return None
        
        # Estrai tutti i campi JSON
        msg = entry.get("msg", "")
        level = entry.get("level", "info")
        size = entry.get("size")
        objectType = entry.get("objectType")
        time = entry.get("time")
        source_code = entry.get("source")
        
        # FILTRO: Ignora operazioni directory metadata (non sono file operations)
        if msg == "Set directory modification time":
            return None
        
        # FILTRO: Ignora messaggi informativi che non sono operazioni
        if msg in ["File is new", "Queue copy to", "Do queued copies to", 
                   "Building Path1 and Path2 listings", "Bisync successful"]:
            return None
        
        # Determina azione da messaggio
        action = RcloneOutputAdapter._determine_action(msg.lower(), level)
        if not action:
            return None
        
        # Determina status dal level
        status = "failed" if level == "error" else "success"
        
        # Crea FileState (legacy, mantenuto per compatibilità)
        # Per copy/update: source exists, dest might exist
        # Per delete: source might not exist, dest exists
        if action in ("copy", "copied"):
            source_state = FileState(exists=True, size=size)
            dest_state = FileState(exists=False)
        elif action in ("delete", "deleted"):
            source_state = FileState(exists=False)
            dest_state = FileState(exists=True, size=size)
        elif action in ("update", "updated"):
            source_state = FileState(exists=True, size=size)
            dest_state = FileState(exists=True)
        else:
            source_state = FileState(exists=True, size=size)
            dest_state = FileState(exists=True)
        
        # Crea FileOperation con TUTTI i campi JSON
        return FileOperation(
            # Legacy fields (per compatibilità)
            path=obj,
            action=action,
            source=source_state,
            destination=dest_state,
            status=status,
            error=entry.get("error"),
            timestamp=time or datetime.now().isoformat(),
            
            # NEW: Campi JSON diretti (usati in to_dict se presenti)
            json_object=obj,
            json_msg=msg,
            json_level=level,
            json_size=size,
            json_objectType=objectType,
            json_time=time,
            json_source=source_code,
        )
    
    @staticmethod
    def _determine_action(msg: str, level: str) -> Optional[str]:
        """
        Determina azione da messaggio rclone.
        
        Args:
            msg: Message field dal log rclone (lowercase)
            level: Log level (info, error, etc.)
        
        Returns:
            Action string (copy, delete, update, etc.) o None
        
        Rclone Messages:
            - "Copied (new)" → copy
            - "Copied (replaced existing)" → update
            - "Deleted" → delete
            - "Moved" → rename
            - "Failed to copy" → error
        """
        if level == "error":
            return "error"
        
        # Map message keywords to actions
        if "copied" in msg or "copy" in msg:
            if "replaced" in msg or "existing" in msg:
                return "update"
            return "copy"
        elif "deleted" in msg or "delete" in msg:
            return "delete"
        elif "moved" in msg or "renamed" in msg:
            return "rename"
        elif "updated" in msg or "update" in msg:
            return "update"
        
        # Unknown message type
        return None
