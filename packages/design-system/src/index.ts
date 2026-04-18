export * from './tokens';
// Components are re-exported below as they land.
export { Button, type ButtonProps, type ButtonVariant, type ButtonSize } from './components/button';
export { Input, type InputProps } from './components/input';
export { Card, CardHeader, CardBody, CardFooter, type CardProps } from './components/card';

// Plan 2 — primitive expansion.
export { Badge, type BadgeProps, type BadgeTone } from './components/badge';
export { StatusBadge, type StatusBadgeProps, type StatusKind } from './components/status-badge';
export { Avatar, type AvatarProps, type AvatarShape, type AvatarSize } from './components/avatar';
export { Kbd, type KbdProps } from './components/kbd';
export { Skeleton, type SkeletonProps, type SkeletonRounded } from './components/skeleton';
export {
  SegmentedControl,
  type SegmentedControlProps,
  type SegmentedControlOption,
} from './components/segmented-control';
export {
  Modal,
  ModalTitle,
  ModalDescription,
  ModalBody,
  ModalFooter,
  type ModalProps,
} from './components/modal';
export {
  ToastViewport,
  toast,
  useToasts,
  dismissToast,
  pushToast,
  type ToastItem,
  type ToastTone,
} from './components/toast';
export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from './components/dropdown-menu';
export { Tooltip, TooltipProvider, type TooltipProps } from './components/tooltip';
export { Tabs, TabsList, TabsTrigger, TabsContent } from './components/tabs';
export {
  BreathingPulse,
  type BreathingPulseProps,
  type BreathingTone,
  type BreathingSize,
} from './components/breathing-pulse';

// Plan 5 — Axis-native primitives.
export { AgentStateDot, type AgentStateDotProps, type AgentState } from './components/agent-state-dot';
export { CitationChip, type CitationChipProps } from './components/citation-chip';
export { PromptInput, type PromptInputProps } from './components/prompt-input';
export { DiffViewer, type DiffViewerProps, type DiffLine, type DiffLineType } from './components/diff-viewer';
export { WritePreviewCard, type WritePreviewCardProps, type WritePreviewMeta } from './components/write-preview-card';

// Plan 7 — Axis-native primitives.
export {
  PermissionCard,
  type PermissionCardProps,
  type PermissionLifetime,
  type PermissionDecision,
} from './components/permission-card';
export {
  LiveTaskTree,
  type LiveTaskTreeProps,
  type StepData,
  type StepState,
  type StepToolCall,
} from './components/live-task-tree';

export {
  TargetPicker,
  type TargetPickerProps,
  type TargetCandidate,
} from './components/target-picker';
