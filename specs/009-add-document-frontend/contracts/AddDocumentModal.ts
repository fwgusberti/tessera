/**
 * Contract for the AddDocumentModal component.
 *
 * This file documents the public interface (props) of the modal
 * and the shape of data passed to the onCreated callback.
 */

import type { Document, Space } from "@/lib/types";

/**
 * Props accepted by AddDocumentModal.
 */
export interface AddDocumentModalProps {
  /** Controls modal visibility. When false the component renders nothing. */
  open: boolean;

  /** Available spaces to display in the space selector. */
  spaces: Space[];

  /** Called when the modal should be dismissed without saving (Cancel / Escape). */
  onClose: () => void;

  /**
   * Called after a document is successfully created.
   * Receives the newly created Document so the parent can prepend it to its list.
   */
  onCreated: (document: Document) => void;
}
