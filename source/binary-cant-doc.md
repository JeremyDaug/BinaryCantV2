[https\://docs.google.com/spreadsheets/d/192D1ekXBeK6YB7V0kIdmwViQHCTpGR2tneWcZGXtzPc/edit?usp=sharing](https://docs.google.com/spreadsheets/d/192D1ekXBeK6YB7V0kIdmwViQHCTpGR2tneWcZGXtzPc/edit?usp=sharing)

XML Examples  
**Example words**  
    **Defined Word**  
\<word text=’self’ grammar=’subject’ tense=’present’/\>   
\<word grammar=’object’\>Ball\</word\>  
    **Typed Word**  
\<word type=’int’ grammar=’object’\>101\</word\>  
\<word text=’123’ type=’int’ grammar=’verb’/\>

**Example external inclusions**  
\<ext type=’jpg’ scr=’thatplace/thisDir/something.jpg’/\>  
\<ext type=’skey’ text=’12345678901234567890’ /\>

**Example Sentences**  
    **Wordless Sentence**  
\<sentence src=’Name’ type=’imperative’/\>  
    **Sentence (with words skipped)**  
\<sentence type=’subjectquery’\> \[words\] \</sentence\>

**Example Cant**  
    **Empty Cant**  
\<cant id=’15’ author=’someone’/\>  
\<cant id=’16’ author=’someoneElse’ dict=’Variant2.cantdb’\> \</cant\>  
    **Non-empty Cant**  
\<cant id=’21’ author=’ThatGuy’\> \[sentences\] \</cant\>

XML format

\<cant id=ID author=CDATA dict=URI\|URL\>  
    \<sentence(s). . . \>  
\</cant\>

\<sentence scr=key\|string\|IDREF type=enum affect=enum evidence=enum\>   
    \<word(s) . . . /\> / \<sentence (s). . ./\>  
\</sentence\>

\<word text=\#PCDATA tense=enum completion=enum recurrence=enum degree=enum emphasis=bool determinative=bool plurality=enum\|value/\>

\<word text=\#PCDATA tense=enum completion=enum recurrence=enum degree=enum emphasis=bool determinative=bool plurality=enum\|value type=string/\>

\<ext type=string src=’URI/URL’ text=string\|value\|raw tense=enum completion=enum recurrence=enum degree=enum emphasis=bool determinative=bool plurality=enum\|value/\>

Cant \| Sentence\*

Sentence \| word\*  
         \| sentence\*  
         \| ext\*

Word

Priorities

* Consistency \- There should never exceptions to the rules if at all possible.  
* Clarity \- There should never be a word with 2 definitions, never be a sentence where the information is not clear.  
* Density \- The language should fit into the word length at all times.   
* Machines first \- Do not bother letting organics talking in it, they are not the target, the machines are.

Rules of Thumb and Guidelines

* You say what something is before it exists.  
* Operate only when everything exists (using Reverse Polish Notation).

Rules

* All sentences must have their length in words attached to them.  
* You may nest something inside a sentence that has its own length and it will not count against the sentence. IE A sentence of length 10, may have another sentence of length 15 within it and the nested sentence only counts as 1 in the word.  
* Scopes and contexts. When nesting sentences the internal sentence shares context with the outer one. Using this allows expansions on information without stating it again. This is most useful for sentences that share topics and splitting the dialog into multiple paragraphs. Once you leave a context any changes revert, similar to how variables scope.

Scratch Space  
    All words start with a flag saying whether the word is inside or outside the language, allowing for arbitrary inclusions (you could include literal ascii, UTC, images, gifs, hyperlinks, effectively anything). While his wordis word would have some rules, it would not be as important as what it precedes.  
    Every sentence is treated like a file, and so it starts with it's metadata. Within the metadata word is sentence type (query statement exclamation imperative and a number of subtypes) Affection (emotion or state in which the sentence is being said),  evidentiality (what is the source of the sentence), and word count currently. Word count is on how many words before the end, with the asterisk that an external inclusion (such as a file) is not included in this length.

Structure  
    Pragmatic Structure  
No defined word order in sentences, instead the word’s grammatical information is attached to the word. 

Sentence Metadata  
    Sentences start with all of the data they need for the sentence, including what kind of sentence, the affection of the sentence, the evidentiality of it, and how many words are in it.  
    Sentences can be nested in other sentences and when done so a sentence encapsulates its own sentence into 1 effective word for the parent. 

Binary logic  
    (X snip ending, Y arbitrary value.)  
    Inside language 	\- 0YYY YYYY YYYY YYYY  
        Sentence Metadata No  	\- 00YY YYYY YYYY YYYY  
            Grammar flags  
                Subject	\- 0000 0YYY YYYY YYYY  
                Object	\- 0000 1YYY YYYY YYYY  
                Topic	\- 0001 0YYY YYYY YYYY  
                Verb	\- 0001 1YYY YYYY YYYY  
                Modifier 	\- 0010 0YYY YYYY YYYY  
                Relation	\- 0010 1YYY YYYY YYYY  
                \[Empty\]	\- 0011 0YYY YYYY YYYY  
                \[Empty\]	\- 0011 1YYY YYYY YYYY  
            Temporal Aspect  
                Timeless	\- 00YY Y00Y YYYY YYYY  
                Past	\- 00YY Y01Y YYYY YYYY  
                Present	\- 00YY Y10Y YYYY YYYY  
                Future	\- 00YY Y11Y YYYY YYYY  
            Progression/Completeness  
                Unprogressed	\- 00YY YYY0 0YYY YYYY  
                Unstarted	\- 00YY YYY0 1YYY YYYY  
                In progress	\- 00YY YYY1 0YYY YYYY  
                Complete	\- 00YY YYY1 1YYY YYYY  
            Recurrence  
                Non-recurring	\- 00YY YYYY Y00Y YYYY  
                Irregular	\- 00YY YYYY Y01Y YYYY  
                Continuous	\- 00YY YYYY Y10Y YYYY  
                Habitual	\- 00YY YYYY Y11Y YYYY  
            Degree/Intensity  
                Unspecified	\- 00YY YYYY YYY0 00YY  
                None/Non-existant	\- 00YY YYYY YYY0 01YY  
                Minimal/Insignificant	\- 00YY YYYY YYY0 10YY  
                Small/Little	\- 00YY YYYY YYY0 11YY  
                Medium/Neutral	\- 00YY YYYY YYY1 00YY  
                Large/Significant	\- 00YY YYYY YYY1 01YY  
                Maximal/Almost Complete	\- 00YY YYYY YYY1 10YY  
                Total/Absolute	\- 00YY YYYY YYY1 11YY  
            Emphasis  
                Unemphasized 	\- 00YY YYYY YYYY YY0Y  
                Emphasized 	\- 00YY YYYY YYYY YY1Y  
            Determinative  
                Nonspecific (a/an)	\- 00YY YYYY YYYY YYY0  
                Specific (the)	\- 00YY YYYY YYYY YYY1  
            Plurality  
                Unnumbered \- 00YY  
                Singular \- 01YY  
                Plural (specific) \- 10YY  
                Plural (nonspecific) \- 11YY

        Sentence Metadata Yes \-	\- 01YY YYYY YYYY YYYY  
            Sentence Type  
                Query         	\- 010Y YYYY YYYY YYYY  
                    Subject (Who)    	\- 0100 00YY YYYY YYYY  
                    Object (Whom)    	\- 0100 01YY YYYY YYYY  
                    Clarify (What)   	\- 0100 10YY YYYY YYYY  
                    Time (When)      	\- 0100 11YY YYYY YYYY  
                    Location (Where) 	\- 0101 00YY YYYY YYYY  
                    Reasoning (Why)  	\- 0101 01YY YYYY YYYY  
                    Explain (How)     	\- 0101 10YY YYYY YYYY  
                    Specify (Which)  	\- 0101 11YY YYYY YYYY  
                Statement---- 	\- 011Y YYYY YYYY YYYY  
                    Fact	\- 0110 00YY YYYY YYYY  
                    Fiction	\- 0110 01YY YYYY YYYY  
                    Uncertain   	\- 0110 10YY YYYY YYYY  
                    Condition   	\- 0110 11YY YYYY YYYY  
                    Result      	\- 0111 00YY YYYY YYYY  
                    Imperative  	\- 0111 01YY YYYY YYYY  
                    Exclamatory 	\- 0111 10YY YYYY YYYY  
                    \[Empty\]     	\- 0111 11YY YYYY YYYY  
            Affection  
                Honest (Neutral)	\- 01YY YY00 00YY YYYY  
                Dishonest	\- 01YY YY00 01YY YYYY  
                Happy	\- 01YY YY00 10YY YYYY  
                Sad	\- 01YY YY00 11YY YYYY  
                Fear	\- 01YY YY01 10YY YYYY  
                Anger	\- 01YY YY01 11YY YYYY  
                Anticipation	\- 01YY YY10 00YY YYYY  
                Surprise	\- 01YY YY10 01YY YYYY  
                Benevolent	\- 01YY YY10 10YY YYYY  
                Malice	\- 01YY YY10 11YY YYYY  
                Pain	\- 01YY YY11 00YY YYYY  
                Pleasue	\- 01YY YY11 01YY YYYY  
                \[Empty\]	\- 01YY YY11 10YY YYYY  
                \[Empty\]	\- 01YY YY11 11YY YYYY  
            Evidentiality  
                Observation (Direct)	\- 01YY YYYY YY00 0YYY  
                Hearsay (Quotation)	\- 01YY YYYY YY00 1YYY  
                Expectation (assumption)	\- 01YY YYYY YY01 0YYY  
                Conclusion (Based on evidence)	\- 01YY YYYY YY01 1YYY  
                Generalization	\- 01YY YYYY YY10 0YYY  
                Postulate (Theory)	\- 01YY YYYY YY10 1YYY  
                Opinion	\- 01YY YYYY YY11 0YYY  
                \[Empty\]	\- 01YY YYYY YY11 1YYY  
Outside Language \- 1X  
    Extension  
    Reference

Colors  
Colors have the last 24 digits reserved for the values. The version can be chosen from RGB, HSL, CMY, and expanded. Expanded ignores the last 24 digits, instead using the next words, depending on the format. Any format should be valid.  
Directionality  
Directionality is handled in a few ways. The built in format is Euler angles and goes z-y-z, or more normally, yaw, pitch, and roll (yypprr) It does does it in half steps making each individual step equal to 1.40625 degrees, or tau/2^8. It can be marked for expansion if to give more room and accuracy.  
For directions (NSEW) you only need the second byte.  
Numbers  
Numbers come in only a few formats naturally. Integer, float, complex, and rational. As usual the first 8 bits are reserved for metadata, and the last 24 are for the value.  
Integer is a signed 23 bit value.  
The float has 1 signed bit, 6 bits of exponent, and 17 bit Mantissa.  
Complex has a 12 bit signed in for real, then 12 bit signed into for imaginary.  
Rational has a 1 sign bit, 11 unsigned it value, then 12 bit unsigned value.  
Elements and Chemical Bonds  
There are 2 branches of this. Atomic, and Compound names.  
Atomic names are singular, but contain all necessary info to define an atom.   
Compounds are multiple word structures and include both elements in the compound, and how they are structured.  
Time  
    Raw time is the number of seconds since  
Operations  
    Operations are special modifiers which don’t count as words as they take previous words and modify them. For example it can add 2 words together. It is also used to apply grammar and other such data to data  from outside the language, allowing you to turn a color into a topic or a number into an object. Each has preexisting rules as to how it acts  
IDs (Specific names)

Complete external  
      
Format groupings  
Color 	0b1000 YYYY \- 0x80  
RGB 	0x80 RR GG BB  
HSL 	0x84 HH SS LL   
YUV 	0x88 YY UU VV  
YCbCr 	0x8C YY Cb Cr  
Direction 	0b1001      \- 0x9  
Objective/contextual 	0b1001 0YYY \- 0x90  
Objective in this case means  
The most common directional  
System, on a planet it would  
be 0 at north, vertical is up.  
Relative 	0b1001 1YYY \- 0x98  
From 	0b1001 Y0YY \- 0x90  
To 	0b1001 Y1YY \- 0x94  
Speaker 	0b1001 YY00 \- 0x90  
Listener 	0b1001 YY01 \- 0x91  
Actor/Subject 	0b1001 YY10 \- 0x92  
Object 	0b1001 YY11 \- 0x93  
Number 	0x1010      \- 0xA  
Integer 	0b1010 00YY \- 0xA0  
Float 	0b1010 01YY \- 0xA4  
Complex 	0b1010 10YY \- 0xA8  
Rational 	0b1010 11YY \- 0xAC  
Constants	See elsewhere  
    Elements and Molecules	0b1011      \- 0xB  
        Atom 	0b1011 0YYY \- 0xB0  
            Protons \= P, Neutrons \= N, Electrons \= E  
              0b1011 0PPP PPPP PPNN NNNN NNNE EEEE EEEE  
            All can be between 0 and 512\.  
        Compounds	0b1011 1YYY \- 0xB8  
            Number of words \+ 1 \= N (counts up from 1 as  
            no compound has 0 atoms) (up to 134,217,728 words allowed)  
              0b1011 1NNN NNNN NNNN NNNN NNNN NNNN NNNN  
            Words in the Compound are as follows  
              Bond type 1 \= B (Ionic, Covalent, Metallic, or \[Empty\])  
              Bonds 1 \= N  
              Bond type 2 \= Q  
              Bonts 2 \= M  
              Element (Proton Count) \= P  
              Molecules form a tree structure where  
              each word creates a sublist  
              of its children.  
              0bBBNN NNQQ MMMM PPPP PPPP PPPP PPPP PPPP   
              From there the compound forms a tree   
              structure until it is complete.  
    Time  
        Raw  
        Formatted  
    Operations  
        Add  
        Subtract  
        Multiply  
        Divide  
        Exponentiation  
        Logarithm  
        Natural Logarithm  
        Binary Logarithm  
        To Subject  
        To Object  
        To Topic  
        To Verb  
        To Modifier  
        To Relation  
        And  
        Or  
        Not  
        Nand  
        Nor  
        Xand  
        Xor  
        Conditional Evaluation  
    Word   
        Constant/abstract  
        Object/Location  
        Operation/action  
        Reference/relation

Words Methodology  
  0b00       \|00 0000 0000 \|0\|0\|00  
    Plurality\|             \| \| \|Word Category  
    Abstract	\- YYYY YYYY YYYY YY00  
        Null	\- 0000 0000 0000 0000  
        Abstract \- 0000 0000 0000 0100  
        Everything \- 1111 1111 1111 1100  
    Object/Location	\- YYYY YYYY YYYY YY01  
        Object	\- YYYY YYYY YYYY Y001  
            Nothing	\- 0000 0000 0000 0001  
            Everything \- 1111 1111 1111 1011  
        Location	\- YYYY YYYY YYYY Y101  
            Nowhere	\- 0000 0000 0000 0101  
            Everywhere \-   
    Action	\- YYYY YYYY YYYY YY10  
        Nothing	\- 0000 0000 0000 0010  
    Relation	\- YYYY YYYY YYYY YY11  
        Unrelated	\- 0000 0000 0000 0011

Example sentences  
    What is that?  
        Query\<Clarify, Honest, Direct, 0\> \- 0x48 00 00 00  
    Nothing is happening.  
        Statement\<Fact, Dishonest, Direct, 1\> Nothing\<Verb, Present, Unprogressed, Non-Recurring, Unspecifed, Unemphasized, Nonspecific\>  
        \|+0x60 40 00 01-0b0110 0000 0100 0000 0000 0000 0000 0000 0001  
        \|+0x1C 00 00 02-0b0001 1100 0000 0000 0000 0000 0000 0000 0010  
    His Shirt is red.  
        \|+0x  
        \|+0x

64  
00000000  
00000000  
00000000  
00000000  
00000000  
00000000  
00000000  
00000000

0000  
0000  
0000  
0000

Binary Cant V2.0

* Binary cant is a language built around the 64 bit word and designed for machines first and foremost.  
* Speech is like a file, where it contains metadata for the speech to follow,  specifically it stores the length of the entire speech event. This uses the absolute length of the file.  
* Sentences include the number of words inside themselves. External inclusions, sentences, and operations do not count in this length. External inclusions and sentences count as 1 word, regardless of their length for a sentence, but their length counts for the full conversation. Operations don’t count as they have absolutely no meaning on their own, rather they expressly alter on other real words. This is so updating the sentences and file size are easy.  
* Sentences act like scopes or contexts do in programming languages, as long as you are within a sentence the information and values are considered the same as the external context until this inner overrides it. This overriding does not flow outwards however, when a sentence ends, all of its information is considered to be either gone or reverted to the previous version.  
* Contextual information and assumptions should minimized when possible. While the language does not require context to function there are guidelines for how a sentence should function.  
  * A Statement of fact, fiction, or uncertainty must result in Data being updated, or in the completion of previously unanswered questions.   
  * Imperatives are commands to the listener if no object is specifying who is being commanded.   
  * Exclamations are like imperatives directed at the speaker.  
  * Queries state which part of the information they are missing, the rest of the sentence is used to specify in more detail. If no specification is given it applies itself to the previous sentence. If no sentence proceeds then it directs the query at the listener.  
* Conversations are any self contained communication file.   
  * A monologue is a conversation where there is only one speaker in the entire conversation, a listener is not required and a speaker need only be specified once.   
  * A dialogue is a conversation where two or more speakers exist. Changing speaker simply requires denoting speakers before they begin.   
* The global scope of a conversation, when given no speaker is treated as a non-entity called the Narrator. What they say is not spoken or listened to, but sets the information for the rest of the conversation. This only applies to Dialogues.  
* Conditions come in concert with the result statements. It follows a strictly If-Then-else structure. If condition, then result, else result. These statements are not evaluated unless the conditional operator is called after them.  
* Subjects are actors, those who do the verb, objects are those who are being acted upon.   
* Verbs are represent a change of state or information. For a word that we don't normally consider to be a verb it represents to be, or to become that word. Ie, John(subject) Billy(verb) would mean John is becoming Billy.  
* Topics are that which the conversation relates to, but doesn't directly talk about.  
* Modifiers act like adjectives and adverbs, altering the meaning of the word before them.  
* Relationships are how subject and object relate to each other. Ie, John(subject) Billy(object) parent(relationship) states that John is Billy's parent.  
* Words in Binary Cant have exactly 1 meaning.  
* A word is prefaced by whether it is prebuilt or an import. These words are called external words and include more complex or esoteric words.  
* Operations calls are a special case of external words in that they are operations that are run at read time. 

    Sentence Metadata 	0x8000 0000 0000 0000  
        Sentence Type	  
            Query         	0x8000 0000 0000 0000  
                Subject (Who)    	0x8000 0000 0000 0000  
                Object (Whom)	0x8800 0000 0000 0000  
                Verb (What)  	0x9000 0000 0000 0000   
                Time (When)     	0x98  
                Location (Where)	0xA0  
                Reasoning (Why)  	0xA8  
                Explain (How) 	0xB0  
                Specify (Which)	0xB8  
            Statement---- 	0xC0  
                Assertion 	0xC0  
                Deletion   	0xC8  
                Condition   	0xD0  
                Result      	0xD8  
                Imperative  	0xE0  
                Exclamatory 	0xE8  
                Uncertain	0xF0  
                \[empty\] (correction)?	0xF8  
        Affection  
            Honest (Neutral)	0x800  
            Dishonest	0x808  
            Happy	0x810  
            Sad	0x818  
            Fear	0x820  
            Anger	0x828  
            Anticipation	0x830  
            Surprise	0x838  
            Benevolent	0x840  
            Malice	0x848  
            Pain	0x850  
            Pleasure	0x858  
            \[Empty\]	0x860  
            \[Empty\]	0x868  
            \[Empty\]	0x870  
            \[Empty\]	0x878  
        Evidentiality  
            Observation (Direct)	0x800  
            Hearsay (Quotation)	0x801  
            Expectation (assumption)	0x802  
            Conclusion (Based on evidence)	0x803  
            Generalization	0x804  
            Postulate (Theory)	0x805  
            Opinion	0x806  
            \[Empty\]	0x807

1. Inside language  
   1. Sentence Metadata No  
      1. Grammar flags  
         1. Subject  
            1. Subject is the actor of the sentence, there may be more than one Subject.   
         2. Object  
            1. Object is what is being acted upon. There may be more than one object.  
         3. Topic   
            1. Topic is what the conversation as a whole is related to, there can be more than one topic, but this is often not suggested.  
         4. Verb  
            1. Verb is the action being done by Subject(s) and to Object(s). When used with Object words it is comparable to ‘to be’, when used with relations it means ‘acts like a’, when used with locations it means ‘to go to’.  
         5. Modifier  
            1. Modifier is similar to adjectives and adverbs, and modifier stack through each other, IE, Jim\<S\> Cat\<M\> Red\<M\> Quetzalcoatl\<M\> all apply to Jim\<S\>. Anything but a Modifier will stop this chain.  
         6. Relation  
            1. Relation is distinct from a verb or Modifier in that it is a relative state between two static entities. The Relation is applied to all preceding Subjects and objects. IE Jim\<s\> Carol\<obj\> Couple\<Rel\> Jack\<obj\> Family\<Rel\> translates as Jim and Carol are a Couple and Jack and Carol are Jim’s family.  
         7. Fusion  
            1. A fusion is like a modifier, but rather then applying attributes to the parent word, it combines with it. IE Jim\<S\> Cat\<m\> Red\<m\> Quetzalcoatl\<m\> is Red cat-like, Quetzalcoatl-like Jim, but Jim\<s\> cat\<f\> red\<f\> Quetzalcoatl\<f\> is Jim-Cat-Quetzalcoatl-Red. Like Modifiers, Fusions stack with other fusions, but act upon anything else.  
         8. \[Empty\]  
      2. Temporal Aspect  
         1. Timeless  
            1. There is no specific time tied to the word.  
         2. Past  
            1. It relates to the word in the past. For Subject, object, or verb, it denotes a previous state of the entity. For Verbs and relations in denotes a prior action or relation.  
         3. Present  
            1. Relates to a current point in time, it may not apply to the past or future. For Subjects, Objects, and Topics it denotes a current state for them. For Verbs and Relations it denotes a current action or relation.  
         4. Future  
            1. Relates to a coming point in time. For Subjects, Objects, and Topics, it relates to a future state of being. For Verbs and Relations it is an action or relation that will come to be.  
      3. Progression/Completeness  
         1. Unprogressed  
         2. Unstarted  
         3. In progress  
         4. Complete  
      4. Recurrence  
         1. Non-recurring  
         2. Irregular  
         3. Continuous  
         4. Habitual  
      5. Degree/Intensity  
         1. Unspecified  
         2. None/Non-existant  
         3. Minimal/Insignificant  
         4. Small/Little  
         5. Medium/Neutral  
         6. Large/Significant  
         7. Maximal/Almost Complete  
         8. Total/Absolute  
      6. Emphasis  
         1. Unemphasized   
            1. The word has no extra emphasis or importance in the statement.  
         2. Emphasized  
            1. The word is important in the sentence and has extra emphasis on it. IE, I ran home vs *I* ran home vs I *ran* home vs I ran *home.*  
      7. Determinative  
         1. Nonspecific (a/an)  
            1. Denotes that the word is not talking about any singular thing in particular. (A cat)  
         2. Specific (the)  
            1. Denotes the word as being directed at a specific item of the word. (The cat)  
      8. Plurality  
         1. Unnumbered  
            1. There is no amount tied to the word meaningfully.  
         2. Singular  
            1. There is only one of the word. Cat  
         3. Plural (nonspecific)  
            1. There is some number of the word. Cats  
         4. Plural (specific)  
            1. There is a specific number of the word. 10 Cats

External functionality is the group of actions and words entirely outside the language, these act as inline operators, allowing you to alter words at runtime.

* Operators and functions

External words

* Colors  
  * RGBA  
  *   
* Directionality  
* Numbers  
* Elements/Compounds  
* Time  
* Operations  
* Pointer  
* Characters  
* IDs  
* Signatures  
* Coordinates

1. Sentence Metadata 	  
   1. Sentence Type	  
      1. Query  \-- Sentence creates an incomplete statement. The subtype defines what is being sought.	  
         1. Subject (Who)  
            1. The question is directed at the actor.  
         2. Object (Whom)  
            1. The Question is directed at the object.  
         3. Verb (What)  	  
            1. The question is directed at the action.  
         4. Time (When)  
            1. Question is directed at the time of the topic.  
         5. Location (Where)	  
            1. Question is directed at the location.  
         6. Reasoning (Why)  	  
            1. Question is directed at the logic of what occured.  
         7. Explain (How)  
            1. Question is directed at how what occured. 	  
         8. Specify (Which)	  
            1. Question is directed at specifying out of a set.  
      2. Statement \-- States the sentence as an idea without direct questioning.	  
         1. Assertion  
            1. Asserts a statement as wholly true.  
         2. Deletion   	  
            1. Removes a previous statement entirely, resetting it’s value.  
         3. Condition  
            1. Denotes the sentence as having a value dependent on it’s factuality.  
         4. Result  
            1. Denotes the sentence as a result of a previous statement. When combined it takes a condition it follows if condition then result else result.  
         5. Imperative  
            1. The sentence is a command directed at someone.  
         6. Exclamatory   
            1. A Statement that is more of an aside directed at the speaker.  
         7. Uncertain (Assertion, correction)?  
            1. A Statement with less certainty then an assert.  
         8. Undefined (correction?  
   2. Affection  
      1. Honest (Neutral)	  
      2. Dishonest	  
      3. Happy	  
      4. Sad	  
      5. Fear	  
      6. Anger	  
      7. Anticipation	  
      8. Surprise	  
      9. Benevolent	  
      10. Malice	  
      11. Pain	  
      12. Pleasure	  
      13. \[Empty\]	  
      14. \[Empty\]	  
      15. \[Empty\]	  
      16. \[Empty\]	  
   3. Evidentiality  
      1. Observation (Direct)  
         1. Standard evidence, speaker holds it as true.	  
      2. Hearsay (Quotation)	  
         1. Heard from someone else.  
      3. Expectation (assumption)	  
         1. A strong belief of things to come.  
      4. Conclusion (Based on evidence)	  
         1. Based on previous evidence.  
      5. Generalization	  
         1. A wide statement based on specific cases.  
      6. Postulate (Theory)	  
         1. A guess  
      7. Opinion  
         1. A subjective opinion.	  
      8. \[Empty\]

Word groupings

1. Object  
   1. Objects are entities which are relatively static in their meaning, objects don’t change. To use as a subject, object, or topic is self explanatory, if subject, they are doing the action, if object, they are being acted upon, if topic they are the overarching conversation context, but may not be directly named. Objects marked as Verbs should are approaching the state of the object, similar to the phrase ‘to be’ in english, IE, You\<S\> Cat\<V\> means you are a cat. Modifier objects are modifiers, similar to ‘like’ in english, IE, You\<S\> Cat\<M\> means you are like a cat.  
2. Location  
   1. A location is like an object, but more nebulous. Unlike objects you can be at a location, but you can't locations cannot be used like a state of being. Subject, object, and topic act like objects. As a verb it acts as where you are, rather than a state you are in. IE, I \<S\> Home \<V\> means ‘I am home’, not ‘I am a Home’. Otherwise this acts like objects do.  
3. Relation  
   1. Relations are like objects, they are states that exist between two objects.   
4. Action  
   1. Actions are things done either by or to something. As verbs they act like 

In general like or related words between these categories should be close to each other. IE, The object manipulator (hand) aligns with the location of your manipulators (in hand), which aligns with the relationship of manipulator (Someone who manipulates something else), which aligns with the act of manipulation (using someone).

Word defaults-

* Assume neutrality, unless the word states otherwise do not ascribe a something to it.   
* Go with a general and more applicable case. There is you don't have a hand, you have a manipulator that is also a grasping 

Examples  
---

1. Grammar flags  
   1. Sub  
   2. Obj  
   3. Top  
   4. Ver  
   5. Mod  
   6. Rel  
   7. Und1  
   8. Und2  
2. Temporal Flags  
   1. \--  
   2. Pas  
   3. Pre  
   4. Fut  
3. Progress  
   1. \--  
   2. Uns  
   3. Pro  
   4. Com  
4. Recurrence  
   1. \--  
   2. Irr  
   3. Con  
   4. Hab  
5. Degree Flags  
   1. \--   
   2. 0  
   3. 1  
   4. 2  
   5. 3  
   6. 4  
   7. 5  
   8. 6  
6. Emphasis  
   1. \--  
   2. \!  
7. Determinative  
   1. \--   
   2. ?  
8. Plurality  
   1. \--  
   2. Sin  
   3. Plu  
   4. Num