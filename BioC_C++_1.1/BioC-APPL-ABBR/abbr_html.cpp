/**** HTML file with PubMed references and abbreviations highlighted
 ****/

#include "BioC.hpp"
#include "BioC_libxml.hpp"
#include "BioC_util.hpp"
#include <iostream>
#include <map>

using std::cerr;
using std::cout;
using std::string;

using namespace BioC;

void html_head(void) {
  cout << "<html>\n"
       << "<head>\n"
       << "<link rel=\"stylesheet\" type=\"text/css\" href=\"abbr.css\" />\n"
       << "<title>PubMed Docs with Abbr</title>\n"
       << "</head>\n"
       << "<body>\n"
       << "<h1>PubMed Docs with Abbr</h1>\n";
}

void html_text( const string & text ) {

  const string special = "<>&\"\'";

  for ( int i = 0; i < text.size(); ++i ) {
    char c = text[i];
    if ( special.find(c) != string::npos )
      cout << "&#" << int(c) << ';';
    else
      cout << c;
  }
    
}

void set_char_state( int loc, int offset, std::map<string,string> & class_map,
                     const vector<Annotation> & annotations,
                     string & new_state ) {
  new_state = "";
  for ( int i = 0; i < annotations.size(); ++i ) {
    const Annotation & note = annotations[i];
    for ( int i_loc = 0; i_loc < note.locations.size(); ++i_loc ) {
      if ( loc >= note.locations[i_loc].offset and
           loc < note.locations[i_loc].offset +
           note.locations[i_loc].length )
        // in note location
        if ( new_state.empty() )
          new_state = class_map[note.id];
        else {
          new_state = "overlap";
          return;
        }
    }
  }
  return;
}  

void html_abbr( const Passage & passage, const Passage & abbr_passage ) {

  // lookup table for span classes

  Seq_ID abbr_id("abbrR");
  std::map<string,string> class_map;
  for ( int i_relation = 0; i_relation < abbr_passage.relations.size();
        ++i_relation ) {
    const Relation & relation = abbr_passage.relations[i_relation];
    string class_name = abbr_id.next(); // relation ID may not be simple integer
    for ( int i_node = 0; i_node <  relation.nodes.size(); ++i_node )
      class_map[ relation.nodes[i_node].refid ] = class_name;
  }

  // assumes the annotations are in loc order and do not overlap

  const string & text = passage.text;
  const int offset = passage.offset;
  int loc = offset;

  // look at all characters in text
  string state = "";            // plain
  int state_begin = 0;
  for ( int i_loc = 0; i_loc < text.size(); ++i_loc ) {
    string new_state;
    set_char_state( i_loc+offset, offset, class_map, abbr_passage.annotations,
                    new_state );
    if ( state == new_state )
      continue;

    // state change
    html_text( text.substr( state_begin, i_loc-state_begin ));
    if ( ! state.empty() )
      cout << "</span>";
    if ( ! new_state.empty() )
      cout << "<span class=\"" << new_state << "\">";
    state = new_state;
    state_begin = i_loc;
  }

  // finish last span
  html_text( text.substr( state_begin, text.size() - state_begin ));
  if ( ! state.empty() )
    cout << "</span>";
}
               
void html( Document & document, const Document & abbr_document ) {

  cout << "<span class=\"id\">PMID: " << document.id << "</span><br>\n";

  if ( document.passages.size() != abbr_document.passages.size() )
    cerr << "doc size diff " << document.passages.size()
         << ' ' << abbr_document.passages.size() << '\n';

  for ( int i = 0; i < document.passages.size(); ++i ) {
    cout << "<div class=\"" << document.passages[i].infons["type"] << "\" >";
    html_abbr( document.passages[i], abbr_document.passages[i] );
    cout << "</div>\n";
  }

}

void html_end(void) {
  cout << "</body>\n"
       << "</html>\n";
}

int main( int argc, char *argv[] ) {
  if ( argc != 3 ) {
    std::cerr << "usage: " << argv[0] << " collection.xml abbr.xml\n";
    return -1;
  }

  char * collection_name = argv[1];
  char * abbr_name = argv[2];
  
  Collection collection;
  Connector_libxml xml;
  xml.start_read(collection_name, collection);

  Collection abbr_collection;
  Connector_libxml abbr_xml;
  abbr_xml.start_read(abbr_name, abbr_collection);
  
  html_head();
  
  Document document;
  while ( xml.read_next(document) ) {
    Document abbr_document;
    abbr_xml.read_next( abbr_document );
    html(document, abbr_document);
  }

  html_end();

  return 0;
}
