/**** Annotate abbreviation long forms and short forms in each passage.
      A relation shows which long and short forms are related.
****/

#include <iostream>
#include <string>
#include <vector>

#include <Ab3P.h>

#include "BioC.hpp"
#include "BioC_libxml.hpp"
#include "BioC_util.hpp"

using std::cout;
using std::string;
using std::vector;

using namespace BioC;

/** comparing ignoring MPtok changing '_' to '-'
 **/
bool MPmatch( const string & orig, const string & MP_str ) {
  if ( orig.size() != MP_str.size() )
    return false;

  for ( int i = 0; i < orig.size(); ++i ) {
    if ( orig[i] == '_' and MP_str[i] == '-' )
      continue;
    if ( orig[i] != MP_str[i] )
      return false;
  }

  return true;
}


class Abbr_Converter : public BioC::Node_Converter {
public:
  using BioC::Node_Converter::convert;

  Abbr_Converter() :
    lf_ids("LF"), sf_ids("SF"), relate_ids("R")
  {}

  virtual void convert( const Passage & passage,
                        Passage & abbrPassage ) {
    abbrPassage.infons = passage.infons;
    abbrPassage.offset = passage.offset;

    vector<AbbrOut> abbrs;
    ab3p.get_abbrs( passage.text, abbrs );

    for ( int i = 0; i < abbrs.size(); ++i ) {

      string abbr_lf =
        passage.text.substr( abbrs[i].lf_offset, abbrs[i].lf.size() );
      string abbr_sf =
        passage.text.substr( abbrs[i].sf_offset, abbrs[i].sf.size() );

      if ( ! MPmatch( abbr_lf, abbrs[i].lf ) ) {
        cerr << "lf miss-match: " << abbr_lf << " -vs- "
             << abbrs[i].lf << '\n';
        exit(-1);
      }
      if ( abbr_sf != abbrs[i].sf ) {
        cerr << "sf miss-match: " << abbr_sf << " -vs- "
             << ' ' << abbrs[i].sf << '\n';
        exit(-1);
      }

      Annotation lf_annote;
      lf_ids.next( lf_annote.id );
      lf_annote.infons["type"] = "ABBR";
      lf_annote.infons["ABBR"] = "LongForm";
      lf_annote.add_location( passage.offset + abbrs[i].lf_offset,
                              abbrs[i].lf.size() );
      lf_annote.text = abbr_lf;

      Annotation sf_annote;
      sf_ids.next( sf_annote.id );
      sf_annote.infons["type"] = "ABBR";
      sf_annote.infons["ABBR"] = "ShortForm";
      sf_annote.add_location( passage.offset + abbrs[i].sf_offset,
                              abbrs[i].sf.size() );
      sf_annote.text = abbrs[i].sf;

      Relation relation;
      relate_ids.next( relation.id );
      relation.infons["type"] = "ABBR";
      relation.nodes.push_back( BioC::Node( lf_annote.id,"LongForm") );
      relation.nodes.push_back( BioC::Node( sf_annote.id,"ShortForm") );

      abbrPassage.annotations.push_back(lf_annote);
      abbrPassage.annotations.push_back(sf_annote);
      abbrPassage.relations.push_back(relation);
    }

  }

  Ab3P ab3p;

  Seq_ID lf_ids;
  Seq_ID sf_ids;
  Seq_ID relate_ids;

};


int
main(int argc, char **argv) {

  if (argc != 2) {
    cerr << "Usage: " << argv[0] << " docname\n";
    return -1;
  }

  char * docname = argv[1];
  
  Collection collection;
  Connector_libxml xml;
  xml.start_read(docname, collection);

  Abbr_Converter converter;
  Collection abbrCollection;
  converter.convert( collection, abbrCollection );
  abbrCollection.key = "abbreviation.key";

  Connector_libxml xml_writer;
  xml_writer.start_write( "-", abbrCollection );
  
  Document document;
  while ( xml.read_next(document) ) {
    Document abbrDocument;
    converter.convert( document, abbrDocument );
    xml_writer.write_next( abbrDocument );
  }
  
  xml_writer.end_write();
  
  return 0;
}
