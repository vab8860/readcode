# ReadCode User Manual (Beginner Friendly)

ReadCode is a programming language that looks like simple English.
If you can write a sentence, you can write a ReadCode program.

This manual is written for complete beginners.

---

## 1. WHAT IS READCODE?

### Vision and goal
ReadCode’s goal is simple:

- Let humans write programs in plain, readable language.
- Remove confusing symbols and “code-heavy” syntax.
- Make it easy to learn, teach, and build real projects.

### Who can use it
ReadCode is for:

- People who never coded before.
- Students and teachers.
- Creators who want to automate small tasks.
- People who want to build a website or a small server quickly.

---

## 2. INSTALLATION

### Install using ReadCodeInstaller.exe

1. Download `ReadCodeInstaller.exe`.
2. Run the installer.
3. After installing, you can open a terminal **anywhere** (Command Prompt or PowerShell).
4. You can run a ReadCode file like this:

```text
readcode myfile.read
```

### Where your programs live
Your `.read` files can be anywhere:

- Desktop
- Documents
- Any folder you like

---

## 3. YOUR FIRST PROGRAM

### Step 1: Create a file
Create a file named `hello.read`.

### Step 2: Write this program

```readcode
say "Hello World"
```

### Step 3: Run it
In your terminal, run:

```text
readcode hello.read
```

You should see:

```text
Hello World
```

---

## 4. COMPLETE SYNTAX (WITH EXAMPLES)

This section is the “dictionary” of ReadCode.
Copy and edit the examples to learn faster.

### 4.1 Variables (store information)

Use `set` or `let`.

```readcode
set name to "Asha"
let age be 18
say name
say age
```

Tips:

- Text must be inside quotes like: `"Hello"`
- Numbers can be written directly like: `10`, `25`

### 4.2 Math

ReadCode uses words for math:

- `plus`
- `minus`
- `times`
- `divided by`

```readcode
set a to 10
set b to 5
say a plus b
say a minus b
say a times b
say a divided by b
```

### 4.3 Input and Output

#### Output
Use `say` or `show`.

```readcode
say "Hello"
show "Hello"
```

#### Input
Use `ask` to get text from the user.

```readcode
ask name
say "Hi " joined with name
```

Important:

- `ask` takes only a variable name (no quotes after it).

### 4.4 Strings (text) and joining text

Use `joined with` to combine text.

```readcode
set first to "Ada"
set last to "Lovelace"
say first joined with " " joined with last
```

#### String operations

```readcode
set s to "Hello"
say uppercase of s
say lowercase of s
say length of s
```

### 4.5 Conditions (if / else)

Conditions let your program make decisions.

Blocks:

- Start with a line ending in `...`
- End with `and end`

```readcode
set age to 20

if the age is greater than 18 ...
say "Adult"
else ...
say "Minor"
and end
```

Comparisons you can use:

- `is equal to`
- `is greater than`
- `is less than`
- `is not equal to`

### 4.6 Loops (repeat / while)

#### Repeat loop

```readcode
repeat 3 times ...
say "Hello"
and end
```

#### While loop

```readcode
set counter to 3
while counter is greater than 0 ...
say counter
set counter to counter minus 1
and end
```

### 4.7 Tasks (functions)

Tasks are reusable groups of steps.

#### Simple task

```readcode
task greet ...
say "Hello!"
and end

do greet
```

#### Task with inputs (parameters) and return value

```readcode
task add_two with x and y ...
set result to x plus y
give back result
and end

set total to run add_two with 7 and 8
say total
```

### 4.8 Lists

Lists hold many values.

```readcode
set nums to list 1 2 3
add 4 to nums
say count of nums
say first item of nums
say last item of nums
show all nums
```

### 4.9 Objects (make your own “things”)

Objects let you create your own types like `Person`, `Car`, `Book`.

```readcode
create object "Person"
add property name
add method greet ...
say "Hello " joined with name
end method
end object

set p to new Person
set p.name to "Ravi"
do p.greet
```

### 4.10 Error handling (try / catch)

Use this when something might fail.

```readcode
try ...
set bad to 10 divided by 0
say bad
catch errors ...
say "Something went wrong, but we recovered."
and end
```

### 4.11 File operations

ReadCode can create, write, read, and delete files.

```readcode
create file "note.txt"
write "Hello file" to file "note.txt"
read file "note.txt" into content
say content
delete file "note.txt"
```

---

## 5. WEB DEVELOPMENT (WEBSITES)

ReadCode can generate a website when your file contains `create page`.

### A simple webpage

```readcode
create page "Home"
set title to "My Website"
set background color to "#0f172a"
set font color to "#e2e8f0"
add heading "Welcome"
add text "This site was created with ReadCode."
add button "Learn More"
end page
```

Run it:

```text
readcode home.read
```

ReadCode will generate a folder like `home_site` and open the page in your browser.

### Styling and themes
Common styling features include:

- Background color
- Font color
- Text size and color for paragraphs

### Animations
If your web features support animations in your version, keep animations simple at first:

- Fade in
- Move
- Hover effects

### Forms, navigation, and mobile
Beginner tips:

- Make one page first.
- Then add buttons/links for navigation.
- Keep text large enough for phones.

---

## 6. BACKEND/SERVER (APIs)

ReadCode can start a server when your file contains `create server on port ...`.

### Simple API server

```readcode
create server on port 3000
on get "/" ...
say "Hello from ReadCode Server"
and end
end server
```

Run it:

```text
readcode server.read
```

Then open your browser to:

```text
http://localhost:3000
```

### Database operations
If your server features support a database, you can enable one and store data.

### Login systems
Login systems usually need:

- A user table (username/password)
- A signup route
- A login route
- A way to remember the user (session/token)

---

## 7. AI INTEGRATION

ReadCode can ask an AI model to generate ReadCode for you.

### 7.1 How to use `ask ai`

```readcode
ask ai "write a hello world program"
```

ReadCode will:

- Ask the AI for ReadCode
- Print the generated ReadCode
- Run it automatically

### 7.2 Setup GROQ_API_KEY

1. Create a file named `readcode.config` in your project folder.
2. Put this inside:

```text
GROQ_API_KEY=your_key_here
```

### 7.3 AI examples

```readcode
ask ai "create a program that uses a list and prints the last item"
ask ai "make a simple web page with a button"
```

---

## 8. REAL WORLD EXAMPLES (IDEAS YOU CAN BUILD)

These are bigger projects you can grow step-by-step.

### 8.1 Calculator

```readcode
ask a
ask b
say a plus b
```

### 8.2 Restaurant website
Ideas:

- Home page
- Menu section
- Contact button

### 8.3 Todo app
Ideas:

- Store a list of tasks
- Add a new task
- Show all tasks
- Remove a task

### 8.4 Chat server
Ideas:

- A server that accepts messages
- A page that sends messages
- A list of connected users

---

## 9. TROUBLESHOOTING & FAQ

### “Oops! I don't understand …”
This usually means:

- A keyword is misspelled.
- A block is missing `and end` / `end page` / `end object`.
- You used a form that ReadCode doesn’t support.

### My program is stuck waiting
If you used `ask`, the program will wait for you to type input.
For non-interactive scripts, avoid `ask`.

### AI says it can’t run
Check:

- You have `readcode.config` with `GROQ_API_KEY=...`
- Your internet connection works
- Your API key is correct

### Where do generated websites go?
They are created in a folder named like `<yourfile>_site` next to your `.read` file.

