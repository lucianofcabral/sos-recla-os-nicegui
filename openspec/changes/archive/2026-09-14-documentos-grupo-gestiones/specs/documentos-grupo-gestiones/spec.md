# documentos-grupo-gestiones Specification

## Purpose

Define document linking for 3 Arroyos lotes: group and per-gestión documents, hash/link dedupe, and GRUPO support.

## Requirements

### Requirement: Group document links to group and each gestión

A group-level document in a 3 Arroyos lote MUST link to the GRUPO and to every RECLAMO (gestión) created in that lote.

#### Scenario: Group document visible everywhere

- GIVEN a lote creates a GRUPO and three gestiones
- WHEN a group-level document is attached
- THEN the document links to the GRUPO and to each gestión
- AND no duplicate document rows are stored

### Requirement: Per-gestión document links only to its gestión

A per-gestión document MUST link only to that gestión.

#### Scenario: Per-gestión isolation

- GIVEN a lote with gestiones A and B
- WHEN a document is attached to gestión A
- THEN it links only to gestión A
- AND it is not visible on gestión B or the GRUPO

### Requirement: Hash and link dedupe

Attaching a document whose content hash already exists MUST NOT create a duplicate document or duplicate link.

#### Scenario: Duplicate hash reuse

- GIVEN a document with content hash H is already stored
- WHEN the same content is attached again
- THEN no new document row is created
- AND no duplicate link is created for the same entity

#### Scenario: Atomic shared document

- GIVEN a lote where two gestiones reference the same document content
- WHEN the lote is created
- THEN no error is raised
- AND the whole lote commits as one atomic unit

### Requirement: GRUPO is an allowed document entity

GRUPO MUST be an allowed entity for document attach, list, and remove, with the same semantics as RECLAMO and PERIODO.

#### Scenario: Group document lifecycle

- GIVEN a GRUPO exists
- WHEN a document is attached to the GRUPO
- THEN it is listed for the GRUPO
- AND it can be removed like RECLAMO/PERIODO documents

### Requirement: Lote creation input separates document kinds

The 3 Arroyos lote creation input MUST support group-level documents separate from per-gestión documents.

#### Scenario: Both document kinds

- GIVEN input with one group-level and one per-gestión document
- WHEN the lote is created
- THEN the group document links to GRUPO and all gestiones
- AND the per-gestión document links only to its gestión

### Requirement: Group UI exposes document management

The group UI MUST expose attach, list, and remove of group documents.

#### Scenario: Manage group documents

- GIVEN the group dialog is open
- WHEN the user attaches or removes a document
- THEN the document list updates
- AND the change is persisted

### Requirement: Lote UI separates uploads

The lote UI MUST allow attaching group documents and per-gestión documents separately.

#### Scenario: Separate uploads

- GIVEN the lote dialog is open
- WHEN the user uploads a group document
- THEN it is recorded as a group-level document
- AND a separate per-gestión upload records only that gestión's document

### Requirement: Editable pending gestión

The lote UI MUST allow selecting a pending gestión so its fields load into the form; editing MUST update that pending gestión, not create a duplicate.

#### Scenario: Edit pending gestión

- GIVEN a lote has pending gestiones
- WHEN the user selects one
- THEN its fields load into the form
- AND saving updates that gestión without creating a duplicate

### Requirement: Link removal and file lifecycle

Deleting a document link MUST remove only that link; the file is removed only when no links remain.

#### Scenario: Remove one link

- GIVEN a document linked to two gestiones
- WHEN one link is removed
- THEN the other link remains
- AND the file is retained

#### Scenario: Remove last link

- GIVEN a document with a single remaining link
- WHEN that link is removed
- THEN the file is removed
