---
name: code-style
description: Apply Go code style best practices for openstack-k8s-operators operators based on gopls modernize and openstack-k8s-operators conventions
argument-hint: "[file.go]"
user-invocable: true
allowed-tools: ["Bash", "Read", "Grep", "Glob", "Edit", "MultiEdit"]
context: fork
---

# Code Style for openstack-k8s-operators Operators

This skill applies and enforces Go code style best practices for openstack-k8s-operators operators, following openstack-k8s-operators conventions and gopls modernize recommendations.

## Code Style Guidelines

### 1. **Modern Go Syntax**

Based on gopls modernize and lib-common patterns:

#### Slice Declaration

```go
// Bad: Old style
var items []string = []string{}

// Good: Modern style
var items []string
```

#### Map Declaration

```go
// Bad: Old style
var configs map[string]interface{} = make(map[string]interface{})

// Good: Modern style
var configs = make(map[string]interface{})
```

#### String Building

```go
// Bad: Inefficient concatenation
result := ""
for _, item := range items {
    result += item + "\n"
}

// Good: Use strings.Builder
var builder strings.Builder
for _, item := range items {
    builder.WriteString(item)
    builder.WriteString("\n")
}
result := builder.String()
```

### 2. **Controller-Runtime Patterns**

#### Error Handling

```go
// Good: Proper error wrapping
if err := r.Get(ctx, req.NamespacedName, &instance); err != nil {
    if errors.IsNotFound(err) {
        return ctrl.Result{}, nil
    }
    return ctrl.Result{}, fmt.Errorf("failed to get instance: %w", err)
}
```

#### Logging

```go
// Good: Structured logging with context
log := ctrl.LoggerFrom(ctx).WithValues("instance", instance.Name)
log.Info("Starting reconciliation")
```

#### Status Updates

```go
// Good: Proper status condition handling
meta.SetStatusCondition(&instance.Status.Conditions, metav1.Condition{
    Type:    "Ready",
    Status:  metav1.ConditionTrue,
    Reason:  "ReconciliationSuccessful",
    Message: "Instance successfully reconciled",
})
```

### 3. **Error Handling**

```go
// Bad: capitalized error string
return fmt.Errorf("Failed to create configmap")

// Good: lowercase, no punctuation, wrapped with context
return fmt.Errorf("failed to create configmap: %w", err)
```

```go
// Bad: unnecessary else after error return
if err != nil {
    return err
} else {
    doSomething()
}

// Good: normal flow at minimal indentation
if err != nil {
    return err
}
doSomething()
```

```go
// Bad: discarding errors
result, _ := someFunction()

// Good: always handle errors
result, err := someFunction()
if err != nil {
    return fmt.Errorf("failed to do something: %w", err)
}
```

### 4. **Naming Conventions**

```go
// Bad: non-Go naming
MAX_RETRIES := 3
func GetOwner() string {}
appId := "123"

// Good: MixedCaps, no Get prefix, consistent initialisms
maxRetries := 3
func Owner() string {}
appID := "123"
```

```go
// Bad: long receiver names
func (reconciler *GlanceReconciler) Reconcile(...) {}
func (this *GlanceReconciler) Reconcile(...) {}

// Good: short, consistent receiver (1-2 letters)
func (r *GlanceReconciler) Reconcile(...) {}
```

```go
// Bad: meaningless package names
package util
package common
package helpers

// Good: descriptive, lowercase, single-word
package glance
package endpoint
package condition
```

### 5. **Interface Design**

```go
// Bad: large interface defined in the implementation package
type Storage interface {
    Get(key string) ([]byte, error)
    Set(key string, value []byte) error
    Delete(key string) error
    List(prefix string) ([]string, error)
    Watch(prefix string) <-chan Event
}

// Good: small interface defined by the consumer, only methods actually needed
type Reader interface {
    Get(key string) ([]byte, error)
}
```

```go
// Bad: returning interface
func NewStore() StoreInterface { return &store{} }

// Good: return concrete type, accept interfaces
func NewStore() *Store { return &store{} }
```

### 6. **Context and Concurrency**

```go
// Bad: context as struct field
type Server struct {
    ctx context.Context
}

// Good: context as first parameter
func (s *Server) Process(ctx context.Context, req Request) error {}
```

```go
// Bad: goroutine with unclear lifetime
go func() {
    for {
        doWork()
    }
}()

// Good: clear goroutine lifecycle with context
go func() {
    for {
        select {
        case <-ctx.Done():
            return
        case item := <-ch:
            process(item)
        }
    }
}()
```

### 7. **openstack-k8s-operators Operator Conventions**

#### Finalizer Handling

```go
// Good: Consistent finalizer pattern
const FinalizerName = "operator.openstack.org/finalizer"

if instance.DeletionTimestamp != nil {
    return r.handleDeletion(ctx, &instance)
}

if !controllerutil.ContainsFinalizer(&instance, FinalizerName) {
    controllerutil.AddFinalizer(&instance, FinalizerName)
    return ctrl.Result{}, r.Update(ctx, &instance)
}
```

#### Resource Management

```go
// Good: Proper owner references
if err := ctrl.SetControllerReference(&instance, resource, r.Scheme); err != nil {
    return fmt.Errorf("failed to set owner reference: %w", err)
}
```

### 8. **Testing Patterns**

#### Ginkgo Best Practices

```go
// Good: Descriptive test structure
var _ = Describe("Nova Controller", func() {
    Context("When creating a Nova instance", func() {
        BeforeEach(func() {
            // Setup
        })

        It("Should create required resources", func() {
            // Test implementation
        })
    })
})
```

#### Mock Usage

```go
// Good: Proper interface mocking
//go:generate mockery --name=ServiceInterface --output=../mocks
type ServiceInterface interface {
    CreateService(ctx context.Context, svc *corev1.Service) error
}
```

## Automated Style Fixes

The skill provides automated fixes for:

### 1. **Modernization**

- Convert old slice/map declarations
- Update string concatenation to use strings.Builder
- Fix inefficient loops and patterns
- Apply gopls modernize suggestions

### 2. **Imports**

- Organize imports according to Go conventions
- Remove unused imports
- Group standard, third-party, and local imports

### 3. **Variable Naming**

- Apply Go naming conventions
- Fix exported vs unexported naming
- Ensure consistent abbreviations

### 4. **Function Signatures**

- Add context parameters where missing
- Proper error return patterns
- Consistent receiver naming

## Style Enforcement Tools

### Built-in Analyzers

```bash
# Run style analysis
gopls check <file>

# Apply modernization fixes
gopls fix -a fillstruct,unusedparam <file>

# Check with golangci-lint
golangci-lint run --enable-all
```

### Custom Rules

- openstack-k8s-operators-specific patterns
- Controller-runtime best practices
- OpenStack operator conventions
- lib-common integration patterns

## Integration with Development Workflow

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: go-style-check
        name: Go Style Check
        entry: ./scripts/style-check.sh
        language: script
        files: '\.go$'
```

### IDE Configuration

```json
// VSCode settings for openstack-k8s-operators operators
{
  "go.lintTool": "golangci-lint",
  "go.lintFlags": ["--config", ".golangci.yml"],
  "gopls": {
    "experimentalPostfixCompletions": true,
    "analyses": {
      "unusedparams": true,
      "shadow": true
    }
  }
}
```

## Usage

Invoke `/code-style` to:

1. **Analyze Current Code**: Scan for style issues and improvement opportunities
2. **Apply Automated Fixes**: Fix common patterns and modernize syntax
3. **Generate Style Report**: Detailed analysis with specific recommendations
4. **Create Action Items**: Use TodoWrite to track style improvements

### Examples

```bash
# Analyze entire project
/code-style analyze-project

# Fix specific file
/code-style fix-file controllers/nova_controller.go

# Check against lib-common patterns
/code-style check-libcommon

# Apply gopls modernize
/code-style modernize
```

## Reference

- [Effective Go](https://go.dev/doc/effective_go)
- [Go Code Review Comments](https://go.dev/wiki/CodeReviewComments)
- [Google Go Style Decisions](https://google.github.io/styleguide/go/decisions)
- [lib-common patterns](https://github.com/openstack-k8s-operators/lib-common)
- [gopls modernize](https://github.com/openstack-k8s-operators/lib-common/pull/646)
- [openstack-k8s-operators conventions](https://github.com/openstack-k8s-operators/dev-docs)
- [Controller-runtime best practices](https://book.kubebuilder.io/)
