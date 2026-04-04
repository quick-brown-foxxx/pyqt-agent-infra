# Interaction Recipes

Concrete command sequences for common tasks. Each recipe follows the inspect-interact-verify loop.

## 1. Add an item to a list

Goal: type an item name and click Add.

```bash
# Inspect
qt-ai-dev-tools tree

# Interact -- type into the text field
qt-ai-dev-tools fill "New item" --role "text"
qt-ai-dev-tools click --role "push button" --name "Add"

# Verify
qt-ai-dev-tools text --role "label" --name "Items"    # check count updated
qt-ai-dev-tools tree --role "list item"                # confirm item appears
```

## 2. Fill a form with multiple fields

Goal: populate several text fields and submit.

```bash
# Inspect -- identify all text fields
qt-ai-dev-tools find --role "text" --json

# Interact -- fill each field
qt-ai-dev-tools fill "John Doe" --role "text" --name "Name"
qt-ai-dev-tools fill "john@example.com" --role "text" --name "Email"
qt-ai-dev-tools fill "555-0100" --role "text" --name "Phone"

# Submit
qt-ai-dev-tools click --role "push button" --name "Submit"

# Verify
qt-ai-dev-tools text --role "label" --name "Status"
qt-ai-dev-tools screenshot -o /tmp/form-result.png
```

## 3. Navigate a menu

Goal: open a menu and select an item. Menu items only appear in the AT-SPI tree after the menu is opened.

```bash
# Inspect menu bar
qt-ai-dev-tools tree --role "menu"

# Open the top-level menu
qt-ai-dev-tools click --role "menu" --name "File"

# Re-inspect -- menu items now visible
qt-ai-dev-tools tree --role "menu item"

# Click the target item
qt-ai-dev-tools click --role "menu item" --name "Save As"

# Handle any resulting dialog
qt-ai-dev-tools tree    # look for [dialog] or [file chooser]
```

For submenus, repeat the re-inspect step after each click. Each level of the menu hierarchy only appears after its parent is opened.

## 4. Handle a dialog

Goal: detect and dismiss a modal dialog (message box, confirmation, etc.).

```bash
# Detect -- look for [dialog] or [alert] in the tree
qt-ai-dev-tools tree

# Find dialog buttons
qt-ai-dev-tools find --role "push button"

# Click the appropriate button
qt-ai-dev-tools click --role "push button" --name "OK"

# Verify dismissed -- dialog should be gone from tree
qt-ai-dev-tools tree
```

If the dialog is unexpected, use `key Escape` to dismiss it. Dialogs are modal -- they block interaction with the main window until dismissed.

## 5. Select from a combo box

Goal: open a dropdown and pick an option.

```bash
# Inspect
qt-ai-dev-tools find --role "combo box"

# Open the dropdown
qt-ai-dev-tools click --role "combo box" --name "Country"

# Re-inspect -- dropdown items now visible as menu items
qt-ai-dev-tools tree --role "menu item"

# Click the desired option
qt-ai-dev-tools click --role "menu item" --name "France"

# Verify
qt-ai-dev-tools text --role "combo box" --name "Country"
```

Alternative using keyboard navigation (often more reliable):

```bash
qt-ai-dev-tools click --role "combo box" --name "Country"
qt-ai-dev-tools key Down
qt-ai-dev-tools key Down
qt-ai-dev-tools key Return
```

## 6. Switch tabs

Goal: click a tab and inspect the new content.

```bash
# Find available tabs
qt-ai-dev-tools find --role "page tab"

# Click the target tab
qt-ai-dev-tools click --role "page tab" --name "Settings"

# Re-inspect -- tree content changes after tab switch
qt-ai-dev-tools tree

# Verify the expected content appeared
qt-ai-dev-tools find --role "text" --name "Username"
```

## 7. Interact with a list

Goal: find and select an item in a list widget.

```bash
# Inspect list items
qt-ai-dev-tools tree --role "list item"

# Click to select
qt-ai-dev-tools click --role "list item" --name "Project Alpha"

# Verify selection (check related widgets that update on selection)
qt-ai-dev-tools text --role "label" --name "Selected"
```

Items outside the visible scroll area may not appear in the AT-SPI tree. Scroll to reveal them (see recipe 8).

## 8. Scroll to reveal widgets

Goal: access widgets that are outside the visible area of a scroll pane.

```bash
# Click inside the scroll area to give it focus
qt-ai-dev-tools click --role "scroll pane"

# Scroll down
qt-ai-dev-tools key Page_Down

# Re-inspect -- newly visible widgets now appear
qt-ai-dev-tools tree

# Repeat if the target widget is still not visible
qt-ai-dev-tools key Page_Down
qt-ai-dev-tools tree
```

Use `Page_Down`/`Page_Up` for large jumps and `Down`/`Up` for fine scrolling. Always re-inspect the tree after scrolling.
